"""Tính metric test set theo evaluation_plan §1 — plan 01 §10.

Metric: ViT accuracy · Siamese Recall@10 · ASR WER/CER · Highlight F1/IoU · Mini-GPT ROUGE-L · Two-Tower NDCG@10.
"""

import torch


def accuracy(logits: torch.Tensor, labels: torch.Tensor) -> float:
    return (logits.argmax(-1) == labels).float().mean().item()


def edit_distance(ref: list, hyp: list) -> int:
    """Levenshtein DP — nền của WER/CER."""
    n, m = len(ref), len(hyp)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            cur = dp[j]
            dp[j] = prev if ref[i - 1] == hyp[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return dp[m]


def wer(ref_text: str, hyp_text: str) -> float:
    ref, hyp = ref_text.split(), hyp_text.split()
    return edit_distance(ref, hyp) / max(1, len(ref))


def cer(ref_text: str, hyp_text: str) -> float:
    return edit_distance(list(ref_text), list(hyp_text)) / max(1, len(ref_text))


def recall_at_k(ranked_ids: list[list[int]], relevant: list[set], k: int = 10) -> float:
    """Recall@k chuẩn IR: |rel ∩ top-k| / |rel|, trung bình theo query.

    KHÔNG phải hit-rate (có ≥1 hit → 1). Với 1 relevant/query (Siamese) hai định nghĩa trùng nhau;
    với nhiều relevant/query (Two-Tower, ~10 test positive/user) hit-rate cao gấp ~10× → từng làm
    Recall trong báo cáo T1.7 nhảy 0.04 → 0.68 mà tưởng là do đổi tập user.
    """
    total = 0.0
    for ranked, rel in zip(ranked_ids, relevant):
        if rel:
            total += len(rel & set(ranked[:k])) / len(rel)
    return total / max(1, len(ranked_ids))


def ndcg_at_k(ranked_ids: list[list[int]], relevant: list[set], k: int = 10) -> float:
    import math
    total = 0.0
    for ranked, rel in zip(ranked_ids, relevant):
        dcg = sum(1 / math.log2(i + 2) for i, x in enumerate(ranked[:k]) if x in rel)
        idcg = sum(1 / math.log2(i + 2) for i in range(min(k, len(rel))))
        total += dcg / idcg if idcg > 0 else 0.0
    return total / max(1, len(ranked_ids))


def eval_recommender(
    model,
    user_features: dict,
    video_features: dict,
    train_rows: list[tuple[int, int, int]],
    test_rows: list[tuple[int, int, int]],
    k: int = 10,
    n_users: int | None = None,
    seed: int = 0,
    device: str = "cpu",
) -> dict:
    """NDCG@k/Recall@k của model VÀ popularity baseline trên CÙNG user, CÙNG candidate set.

    Trả cả hai trong một lần gọi để không thể so model với baseline tính rời (bug đã gặp:
    baseline hardcode từ run khác → 'vượt baseline' giả).

    `n_users=None` (mặc định) = chấm TOÀN BỘ user đủ điều kiện → hết nhiễu do sample user, và
    hết cả lớp bug "hai tập user khác nhau". MovieLens-100k chỉ ~280 user có test positive,
    1682 item nên chấm hết vẫn rẻ. Đặt số cụ thể chỉ khi cần chạy nhanh lúc debug.
    """
    import random
    from collections import Counter, defaultdict

    item_ids = sorted(video_features)
    item_index = {i: j for j, i in enumerate(item_ids)}

    relevant_by_user: dict[int, set] = defaultdict(set)
    for u, i, _ in test_rows:
        relevant_by_user[u].add(i)
    seen_by_user: dict[int, set] = defaultdict(set)
    for u, i, _ in train_rows:
        seen_by_user[u].add(i)

    pop_rank = [i for i, _ in Counter(i for _, i, _ in train_rows).most_common()]

    users = sorted(u for u in relevant_by_user if u in user_features)
    n_eligible = len(users)
    if n_users is not None:
        random.Random(seed).shuffle(users)
        users = users[:n_users]
    if not users:
        raise ValueError("không có user nào vừa có test positive vừa có feature")

    model.eval()
    video_matrix = torch.stack([video_features[i] for i in item_ids]).to(device)
    with torch.no_grad():
        item_emb = model.video_embed(video_matrix)

    model_ranked, pop_ranked, relevant = [], [], []
    for u in users:
        with torch.no_grad():
            user_emb = model.user_embed(user_features[u].unsqueeze(0).to(device))
            scores = (item_emb @ user_emb.T).squeeze(1)
        for i in seen_by_user[u]:                       # không gợi lại item đã thấy ở train
            if i in item_index:
                scores[item_index[i]] = float("-inf")
        model_ranked.append([item_ids[j] for j in torch.topk(scores, k).indices.tolist()])
        pop_ranked.append([i for i in pop_rank if i not in seen_by_user[u]][:k])
        relevant.append(relevant_by_user[u])

    return {
        "n_users": len(users),
        "n_eligible": n_eligible,
        "model_ndcg": ndcg_at_k(model_ranked, relevant, k),
        "model_recall": recall_at_k(model_ranked, relevant, k),
        "pop_ndcg": ndcg_at_k(pop_ranked, relevant, k),
        "pop_recall": recall_at_k(pop_ranked, relevant, k),
    }


def format_recommender_report(m: dict) -> str:
    """Verdict T1.7 = NDCG@10 vượt popularity, ĐÚNG evaluation_plan §1 cột 'Mục tiêu chấp nhận'.

    Recall@10 là *metric chính* theo §1 (metric phụ của Two-Tower là Coverage + thời gian truy vấn
    Milvus) nên phải báo cáo — nhưng KHÔNG phải điều kiện pass; bản trước tự thêm rào 'thắng cả
    hai'. Nhãn in ra nói "không phải cổng", tránh hạ Recall xuống hàng metric phụ.
    """
    coverage = f"{m['n_users']}/{m.get('n_eligible', m['n_users'])} eligible users"
    return (
        f"same users ({coverage}), same candidate set\n"
        f"Two-Tower  NDCG@10={m['model_ndcg']:.4f}  Recall@10={m['model_recall']:.4f}\n"
        f"Popularity NDCG@10={m['pop_ndcg']:.4f}  Recall@10={m['pop_recall']:.4f}\n"
        f"NDCG (cổng T1.7): {'PASS' if m['model_ndcg'] > m['pop_ndcg'] else 'FAIL'}"
        f" | Recall (metric chính, không phải cổng):"
        f" {'trên' if m['model_recall'] > m['pop_recall'] else 'dưới'} baseline"
    )


def aggregate_runs(runs: list[dict]) -> dict:
    """mean ± std theo key trên nhiều seed — evaluation_plan §0.3 bắt buộc 3 lần chạy cho Two-Tower.

    Verdict lấy theo mean; 1 seed thắng không phải bằng chứng nếu std cùng bậc với khoảng cách.
    """
    import statistics
    keys = [k for k in runs[0] if isinstance(runs[0][k], float)]
    out = {"n_runs": len(runs)}
    for k in keys:
        vals = [r[k] for r in runs]
        out[k] = statistics.fmean(vals)
        out[k + "_std"] = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return out


def format_seed_report(agg: dict) -> str:
    gap = agg["model_ndcg"] - agg["pop_ndcg"]
    noise = agg["model_ndcg_std"] + agg["pop_ndcg_std"]
    return (
        f"{agg['n_runs']} seed\n"
        f"Two-Tower  NDCG@10={agg['model_ndcg']:.4f}±{agg['model_ndcg_std']:.4f}"
        f"  Recall@10={agg['model_recall']:.4f}±{agg['model_recall_std']:.4f}\n"
        f"Popularity NDCG@10={agg['pop_ndcg']:.4f}±{agg['pop_ndcg_std']:.4f}"
        f"  Recall@10={agg['pop_recall']:.4f}±{agg['pop_recall_std']:.4f}\n"
        f"gap NDCG={gap:+.4f} (std tổng {noise:.4f})"
        f" | T1.7: {'PASS' if gap > 0 else 'FAIL'}"
        f"{'  [gap < noise, chưa kết luận được]' if 0 < gap <= noise else ''}"
    )


def f1_per_second(pred: torch.Tensor, target: torch.Tensor, thresh: float = 0.5, ignore: int = -1) -> float:
    """F1 chấm điểm highlight/giây, bỏ giây ignore."""
    mask = target != ignore
    p = (pred[mask] > thresh).long()
    t = target[mask].long()
    tp = int(((p == 1) & (t == 1)).sum())
    fp = int(((p == 1) & (t == 0)).sum())
    fn = int(((p == 0) & (t == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


def rouge_l(ref: str, hyp: str) -> float:
    """ROUGE-L F1 dựa LCS (đơn vị từ)."""
    r, h = ref.split(), hyp.split()
    n, m = len(r), len(h)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if r[i - 1] == h[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[n][m]
    if lcs == 0:
        return 0.0
    prec, rec = lcs / max(1, m), lcs / max(1, n)
    return 2 * prec * rec / (prec + rec)
