"""AI-12b/12d — Two-Tower v2 for product data: inductive features, training, evaluation harness, D19 gate.

Inductive = towers read features (categories, history, popularity), not one-hot IDs, so new users/videos get vectors.
The architecture is the existing `TwoTower`; only the inputs change. Every feature is built from TRAIN labels only.
Synthetic data may exercise this code but never passes `production_ready` (provenance check, D19).
"""

import math
import platform
import random
import time
from collections import Counter
from dataclasses import dataclass

import torch

from ..config import ModelConfig
from ..models.two_tower import TwoTower
from ..optim import AdamW
from ..scripts.evaluate import ndcg_at_k, recall_at_k
from .datasets import product_interactions as pi
from .loss_fns import two_tower_softmax_loss

FEATURE_VERSION = "ttv2-features-v1"
CONTENT_DIM = 256          # ViT embedding slot; zeros + has_content=0 until a content source exists


@dataclass
class Features:
    vocab: pi.Vocab
    video_ids: list
    video: torch.Tensor     # (V, video_dim): [category one-hot K | has_content | content 256 | log-popularity]
    user: dict              # user_id → (user_dim,): [preferred categories K | mean train-positive video vector | log #positives]
    train_pop: torch.Tensor  # (V,) train positive counts — also the Popularity baseline
    video_dim: int
    user_dim: int
    version: str = FEATURE_VERSION


def _positives(labels):
    return [l for l in labels if l.positive]


def build_features(export: pi.Export, split: pi.Split, content: dict | None = None) -> Features:
    vocab = pi.category_vocab(export)
    k = len(vocab.ids)
    video_ids = sorted(v for v, row in export.videos.items() if row.get("visible_to_client"))
    idx = {v: i for i, v in enumerate(video_ids)}
    train_pos = [l for l in _positives(split.train) if l.video_id in idx]
    counts = Counter(l.video_id for l in train_pos)
    max_log = math.log1p(max(counts.values())) if counts else 1.0
    content = content or {}

    video = torch.zeros(len(video_ids), k + 1 + CONTENT_DIM + 1)
    for i, vid in enumerate(video_ids):
        c = vocab.index(export.videos[vid].get("category_id"))
        if c is not None:
            video[i, c] = 1.0
        if vid in content:
            video[i, k] = 1.0
            video[i, k + 1:k + 1 + CONTENT_DIM] = torch.as_tensor(content[vid], dtype=torch.float32)
        video[i, -1] = math.log1p(counts[vid]) / max_log

    history: dict = {}
    for l in train_pos:
        history.setdefault(l.user_id, []).append(idx[l.video_id])
    max_n = math.log1p(max((len(h) for h in history.values()), default=0)) or 1.0
    user = {}
    for uid, row in export.users.items():
        vec = torch.zeros(k + video.shape[1] + 1)
        for cat in row.get("preferred_category_ids") or []:
            c = vocab.index(cat)
            if c is not None:
                vec[c] = 1.0
        if uid in history:
            vec[k:k + video.shape[1]] = video[history[uid]].mean(0)
            vec[-1] = math.log1p(len(history[uid])) / max_n
        user[uid] = vec
    train_pop = torch.tensor([counts[v] for v in video_ids], dtype=torch.long)
    return Features(vocab, video_ids, video, user, train_pop, video.shape[1], k + video.shape[1] + 1)


def train(features: Features, split: pi.Split, steps: int = 500, batch: int = 128, lr: float = 3e-3,
          seed: int = 0, temperature: float = 0.1, proj_dim: int = 128) -> TwoTower:
    """In-batch softmax with logQ correction (`two_tower_softmax_loss`) on train positives only."""
    torch.manual_seed(seed)
    idx = {v: i for i, v in enumerate(features.video_ids)}
    pairs = [(l.user_id, idx[l.video_id]) for l in _positives(split.train) if l.video_id in idx and l.user_id in features.user]
    if not pairs:
        raise ValueError("no train positives")
    users = torch.stack([features.user[u] for u, _ in pairs])
    items = torch.tensor([i for _, i in pairs])
    freq = torch.bincount(items, minlength=len(features.video_ids)).float()
    log_q_all = torch.log(freq.clamp(min=1) / freq.sum())
    model = TwoTower(ModelConfig(name="two_tower", proj_dim=proj_dim, temperature=temperature),
                     user_dim=features.user_dim, video_dim=features.video_dim)
    opt = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    gen = torch.Generator().manual_seed(seed)
    model.train()
    for _ in range(steps):
        b = torch.randint(len(pairs), (min(batch, len(pairs)),), generator=gen)
        item = items[b]
        loss = two_tower_softmax_loss(model, (users[b], features.video[item], None, log_q_all[item], None, item))
        opt.zero_grad()
        loss.backward()
        opt.step()
    return model.eval()


def model_scorer(model: TwoTower, features: Features):
    with torch.no_grad():
        videos = model.video_embed(features.video)

    def score(user_ids):
        with torch.no_grad():
            return model.user_embed(torch.stack([features.user[u] for u in user_ids])) @ videos.T
    return score


def _bootstrap(diffs: list, n_boot: int, seed: int) -> dict:
    """Paired bootstrap over eval users: resample users, mean of (model − popularity); 95% percentile interval."""
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return {"mean": sum(diffs) / n, "ci95": [means[int(0.025 * (n_boot - 1))], means[int(0.975 * (n_boot - 1))]]}


def evaluate(score_fn, features: Features, split: pi.Split, k: int = 10, n_boot: int = 1000, seed: int = 0,
             provenance: str = "synthetic", data: dict | None = None, latency_users: int = 200) -> dict:
    """Model vs Popularity on the SAME eval users and candidates. Candidates = videos visible at snapshot;
    each user's train positives are removed from both rankings; relevant = the user's eval positives."""
    idx = {v: i for i, v in enumerate(features.video_ids)}
    seen, rel = {}, {}
    for l in _positives(split.train):
        if l.video_id in idx:
            seen.setdefault(l.user_id, set()).add(l.video_id)
    for l in _positives(split.eval):
        if l.video_id in idx and l.user_id in features.user:
            rel.setdefault(l.user_id, set()).add(l.video_id)
    users = sorted(rel)
    if not users:
        raise ValueError("no eval users with eval positives")
    scores = score_fn(users).float()
    pop_order = sorted(features.video_ids, key=lambda v: (-int(features.train_pop[idx[v]]), v))
    per = {"model": {"recall": [], "ndcg": []}, "popularity": {"recall": [], "ndcg": []}}
    shown = set()
    for row, uid in enumerate(users):
        s = scores[row].clone()
        for v in seen.get(uid, ()):
            s[idx[v]] = float("-inf")
        ranked = [features.video_ids[i] for i in torch.topk(s, min(k, len(s))).indices.tolist()]
        ranked = [v for v in ranked if v not in seen.get(uid, ())]
        shown.update(ranked)
        pop = [v for v in pop_order if v not in seen.get(uid, ())][:k]
        for name, r in (("model", ranked), ("popularity", pop)):
            per[name]["recall"].append(recall_at_k([r], [rel[uid]], k))
            per[name]["ndcg"].append(ndcg_at_k([r], [rel[uid]], k))

    def mean(xs):
        return sum(xs) / len(xs)

    def summary(sel):
        return {name: {m: mean([per[name][m][i] for i in sel]) for m in ("recall", "ndcg")} for name in per} if sel else None

    lat = []
    for uid in users[:latency_users]:
        t = time.perf_counter()
        torch.topk(score_fn([uid])[0], min(k, len(features.video_ids)))
        lat.append((time.perf_counter() - t) * 1000)
    lat.sort()
    cold = [i for i, u in enumerate(users) if u in split.cold_start_users]
    return {
        "provenance": provenance, "feature_version": features.version, "label_version": pi.LABEL_VERSION, "k": k,
        "candidates": {"n": len(features.video_ids), "definition": "videos visible_to_client at snapshot; user's train positives excluded"},
        "n_eval_users": len(users), "n_eval_positives": sum(len(r) for r in rel.values()),
        "model": {m: mean(per["model"][m]) for m in ("recall", "ndcg")},
        "popularity": {m: mean(per["popularity"][m]) for m in ("recall", "ndcg")},
        "diff": {m: _bootstrap([a - b for a, b in zip(per["model"][m], per["popularity"][m])], n_boot, seed) for m in ("recall", "ndcg")},
        "ci_method": f"paired bootstrap over eval users, B={n_boot}, percentile 2.5/97.5, seed={seed}",
        "coverage_at_k": len(shown) / len(features.video_ids),
        "latency": {"p95_ms": lat[int(0.95 * (len(lat) - 1))], "n_users": len(lat), "what": "score_fn(1 user) + top-k",
                    "cpu": platform.processor() or platform.machine(), "threads": torch.get_num_threads()},
        "cold_start": {"n_users": len(cold), **(summary(cold) or {})},
        "data": data,
    }


def data_stats(cleaned: pi.Cleaned, labels: list, split: pi.Split) -> dict:
    n_pos = Counter(l.user_id for l in labels if l.positive)
    eval_users = {l.user_id for l in split.eval if l.positive}
    stats = {"n_users": len({r["user_id"] for r in cleaned.interactions}), "n_valid": len(cleaned.interactions),
             "eval_users_with_5_pos": sum(1 for u in eval_users if n_pos[u] >= 5), "dropped": cleaned.dropped}
    stats["stage"] = pi.gate_stage(stats["n_users"], stats["n_valid"], stats["eval_users_with_5_pos"])
    return stats


def production_ready(report: dict) -> tuple[bool, list]:
    """D19 PRODUCTION_READY criteria. Passing means the gate is met — deployment still needs user approval."""
    reasons = []
    if report.get("provenance") != "product_export":
        reasons.append("provenance is not a product export (synthetic/sandbox results never qualify)")
    if (report.get("data") or {}).get("stage") != "EVAL_READY":
        reasons.append("data stage is not EVAL_READY")
    for m in ("recall", "ndcg"):
        if report["diff"][m]["ci95"][0] <= 0:
            reasons.append(f"{m}@k CI95 lower bound of (model − popularity) is not > 0")
    if report.get("coverage_at_k", 0) < 0.2:
        reasons.append("coverage@k < 20%")
    if report["latency"]["p95_ms"] > 50:
        reasons.append("p95 CPU latency > 50 ms/user")
    return not reasons, reasons
