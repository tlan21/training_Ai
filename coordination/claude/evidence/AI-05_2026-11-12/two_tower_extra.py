"""AI-05 round 2: Two-Tower extra metrics on the SAME test protocol as v14 (leave-last-10 twice, seen = fit rows, all 876 users).

Per checkpoint: reproduce NDCG/Recall@10 (must equal the v14 log), coverage@10 (model vs popularity), paired per-user bootstrap CI of
NDCG@10 model - popularity, brute-force query latency (user tower + scoring 1682 items + top-10, CPU, single user).
  python two_tower_extra.py <out.json>
"""
import json
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import torch

sys.path.insert(0, 'E:/traning_ai/ai-core')
from ai_core.config import ModelConfig  # noqa: E402
from ai_core.models.two_tower import TwoTower  # noqa: E402
from ai_core.scripts.evaluate import eval_recommender, ndcg_at_k  # noqa: E402
from ai_core.training.checkpoint import load_checkpoint  # noqa: E402
from ai_core.training.datasets import build_features, leave_last_k_split  # noqa: E402

ML = Path('E:/traning_ai/dist/kaggle/ai-core-ds')
V14 = Path('E:/traning_ai/dist/kaggle/output/v14')
CKPTS = {'seed1337_v14': V14 / 'ckpt_seed1337/two_tower/best.pt', 'seed7_v14': V14 / 'ckpt_seed7/two_tower/best.pt',
         'seed2024_v14': V14 / 'ckpt_seed2024/two_tower/best.pt', 'active_f28c3794': Path('E:/traning_ai/ai-core/checkpoints/two_tower/best.pt')}
LOG = {'seed1337_v14': (0.1019, 0.0944), 'seed7_v14': (0.0969, 0.0889), 'seed2024_v14': (0.0983, 0.0906)}


def bootstrap(diffs, n_boot=2000, seed=1337):
    rng, n = random.Random(seed), len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return [means[int(.025 * (n_boot - 1))], means[int(.975 * (n_boot - 1))]]


def main():
    item_genres = {}
    for line in open(ML / 'u.item', encoding='latin-1'):
        p = line.rstrip('\n').split('|')
        item_genres[int(p[0])] = torch.tensor([float(x) for x in p[-19:]], dtype=torch.float32)
    rows = []
    for line in open(ML / 'u.data'):
        u, i, r, ts = map(int, line.split())
        if r >= 4:
            rows.append((u, i, ts))
    train_rows, test_rows = leave_last_k_split(rows, k=10)
    fit_rows, _ = leave_last_k_split(train_rows, k=10)
    user_feat, video_feat = build_features(fit_rows, item_genres)
    item_ids = sorted(video_feat)
    index = {i: j for j, i in enumerate(item_ids)}
    relevant, seen = defaultdict(set), defaultdict(set)
    for u, i, _ in test_rows:
        relevant[u].add(i)
    for u, i, _ in fit_rows:
        seen[u].add(i)
    users = sorted(u for u in relevant if u in user_feat)
    pop = [i for i, _ in Counter(i for _, i, _ in fit_rows).most_common()]
    pop_lists = [[i for i in pop if i not in seen[u]][:10] for u in users]
    pop_ndcg = [ndcg_at_k([r], [relevant[u]], 10) for u, r in zip(users, pop_lists)]
    report = {'n_users': len(users), 'n_items': len(item_ids),
              'popularity': {'ndcg': statistics.mean(pop_ndcg), 'coverage_at_10': len({i for r in pop_lists for i in r}) / len(item_ids)}}
    torch.set_num_threads(1)
    for name, path in CKPTS.items():
        saved = load_checkpoint(str(path))
        ud, vd = next(iter(user_feat.values())).numel(), next(iter(video_feat.values())).numel()
        cfg = ModelConfig(**saved['config'])
        model = TwoTower(cfg, user_dim=ud, video_dim=vd)
        model.load_state_dict(saved['state_dict'])
        model.eval()
        ref = eval_recommender(model, user_feat, video_feat, fit_rows, test_rows, k=10)
        with torch.no_grad():
            item_emb = model.video_embed(torch.stack([video_feat[i] for i in item_ids]))
        lists, latencies = [], []
        for u in users:
            t0 = time.perf_counter()
            with torch.no_grad():
                scores = (item_emb @ model.user_embed(user_feat[u].unsqueeze(0)).T).squeeze(1)
            for i in seen[u]:
                scores[index[i]] = float('-inf')
            top = torch.topk(scores, 10).indices.tolist()
            latencies.append((time.perf_counter() - t0) * 1000)
            lists.append([item_ids[j] for j in top])
        per_user = [ndcg_at_k([r], [relevant[u]], 10) for u, r in zip(users, lists)]
        diffs = [m - p for m, p in zip(per_user, pop_ndcg)]
        latencies.sort()
        report[name] = {'sha256_prefix': __import__('hashlib').sha256(path.read_bytes()).hexdigest()[:8],
                        'ndcg': ref['model_ndcg'], 'recall': ref['model_recall'], 'pop_ndcg_check': ref['pop_ndcg'],
                        'v14_log': LOG.get(name), 'coverage_at_10': len({i for r in lists for i in r}) / len(item_ids),
                        'delta_ndcg_vs_pop': statistics.mean(diffs), 'delta_ndcg_ci95': bootstrap(diffs),
                        'latency_ms_cpu_1thread': {'p50': latencies[len(latencies) // 2], 'p95': latencies[int(.95 * len(latencies))]}}
        print(name, json.dumps(report[name]), flush=True)
    Path(sys.argv[1]).write_text(json.dumps(report, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
