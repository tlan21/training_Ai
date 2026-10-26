"""T1.7d — export vector 128-d L2-norm của Two-Tower vào Milvus (IP) và kiểm tra truy vấn.

Dùng:
  python -m ai_core.scripts.export_two_tower_milvus \
      --checkpoint D:/.../checkpoints/two_tower/best.pt \
      --ratings dist/kaggle/ai-core-ds/u.data --items dist/kaggle/ai-core-ds/u.item

Mặc định ghi sandbox `sandbox_two_tower_ai09_20261026` (Codex tạo, HC-04); collection sản phẩm bị chặn (D14):
id VARCHAR (PK) | vector 128-d | type ∈ {user, video}, index IVF_FLAT + metric **IP**.

Vì sao IP chứ không phải COSINE: `TwoTower.user_embed/video_embed` đã `F.normalize` nên vector nằm
trên mặt cầu đơn vị, ở đó inner product **bằng** cosine — IP rẻ hơn và khớp đúng cách model được
train (`sim = u·v / temperature`). Script vẫn kiểm lại ‖v‖ ≈ 1 trước khi nạp: nếu tầng normalize
biến mất khỏi model thì IP lặng lẽ thành dot product thô, thứ hạng sai mà không gì báo.

Feature phải dựng từ ĐÚNG `fit_rows` như lúc train (leave-last-k hai lần), nếu không one-hot lệch
chỉ số và vector xuất ra là của item khác.
"""

import argparse
import hashlib
import json
import time

import torch

from ..config import ModelConfig
from ..models.two_tower import TwoTower
from ..training.checkpoint import load_checkpoint
from ..training.datasets import build_features, leave_last_k_split

N_GENRE = 19
# D14 (user 2026-10-26): MovieLens training IDs never go into the product collection — sandbox only.
PRODUCT_COLLECTION = "user_recommendation_embeddings"
SANDBOX_COLLECTION = "sandbox_two_tower_ai09_20261026"     # Codex RE:HC-04, empty, backend never reads it
ARTIFACT_VERSION = "two_tower-ml100k-v1"
DELETE_EXPR = 'id like "ml100k_%"'                         # re-export replaces only our own namespace


def vector_id(kind: str, key: int) -> str:
    """MovieLens index → sandbox ID. Never `usr_*`/`vid_*`: those are product Postgres IDs."""
    return f"ml100k_{'u' if kind == 'user' else 'i'}_{key}"


def check_target(collection: str) -> None:
    if collection == PRODUCT_COLLECTION:
        raise SystemExit(f"D14: không nạp vector MovieLens vào collection sản phẩm {PRODUCT_COLLECTION} — dùng {SANDBOX_COLLECTION}")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def artifact_manifest(ckpt_path, ratings_path, items_path, ids, types, ckpt) -> dict:
    """AI-09 artifact contract: exactly which inputs this checkpoint can encode."""
    cfg = ckpt["config"]
    return {
        "artifact_version": ARTIFACT_VERSION,
        "checkpoint_sha256": _sha256(ckpt_path),
        "ratings_sha256": _sha256(ratings_path),
        "items_sha256": _sha256(items_path),
        "metrics": ckpt.get("metrics"),
        "dim": cfg["proj_dim"], "metric": "IP", "normalization": "L2 (IP == cosine); service score = (IP+1)/2",
        "id_namespace": {"user": "ml100k_u_<movielens user id>", "video": "ml100k_i_<movielens item id>"},
        "counts": {"user": types.count("user"), "video": types.count("video")},
        "encoder_input": {
            "user": {"dim": cfg["user_dim"], "features": "one-hot MovieLens user index (users of fit split, rating>=4, leave-last-10 twice)"},
            "video": {"dim": cfg["video_dim"], "features": f"{N_GENRE} MovieLens genres + log1p(popularity)/max + one-hot MovieLens item index"},
        },
        "unknown_input_policy": "no vector: IDs outside the training vocabulary cannot be encoded (transductive one-hot)",
        "product_ids_supported": False,
    }


def load_movielens(ratings_path: str, items_path: str):
    item_genres = {}
    with open(items_path, encoding="latin-1") as f:
        for line in f:
            p = line.rstrip("\n").split("|")
            if len(p) > N_GENRE:
                item_genres[int(p[0])] = torch.tensor(
                    [float(x) for x in p[-N_GENRE:]], dtype=torch.float32)
    rows = []
    with open(ratings_path, encoding="utf-8") as f:
        for line in f:
            u, i, r, ts = map(int, line.split())
            if r >= 4:
                rows.append((u, i, ts))
    return rows, item_genres


@torch.no_grad()
def build_vectors(ckpt_path: str, ratings_path: str, items_path: str, k: int = 10):
    """→ (ids, vectors, types, ckpt). Vector đã L2-norm, float32."""
    rows, item_genres = load_movielens(ratings_path, items_path)
    train_rows, _ = leave_last_k_split(rows, k=k)
    fit_rows, _ = leave_last_k_split(train_rows, k=k)
    user_feat, video_feat = build_features(fit_rows, item_genres)

    ckpt = load_checkpoint(ckpt_path)
    cfg = ModelConfig(**ckpt["config"])
    user_dim = next(iter(user_feat.values())).numel()
    video_dim = next(iter(video_feat.values())).numel()
    if (cfg.user_dim, cfg.video_dim) != (user_dim, video_dim):
        raise SystemExit(
            f"Feature lệch checkpoint: checkpoint train với user_dim={cfg.user_dim} "
            f"video_dim={cfg.video_dim}, dữ liệu hiện tại {user_dim}/{video_dim}. "
            f"Vector xuất ra sẽ là của item khác — dừng.")
    model = TwoTower(cfg, user_dim=user_dim, video_dim=video_dim).eval()
    model.load_state_dict(ckpt["state_dict"])

    ids, vecs, types = [], [], []
    for kind, feats, embed in (("user", user_feat, model.user_embed),
                               ("video", video_feat, model.video_embed)):
        keys = sorted(feats)
        vecs.append(embed(torch.stack([feats[key] for key in keys])).float())
        ids += [vector_id(kind, key) for key in keys]
        types += [kind] * len(keys)
    vectors = torch.cat(vecs)

    norms = vectors.norm(dim=-1)
    if not torch.allclose(norms, torch.ones_like(norms), atol=1e-4):
        raise SystemExit(f"Vector chưa L2-norm (‖v‖ ∈ [{norms.min():.4f}, {norms.max():.4f}]) — "
                         f"metric IP sẽ không còn bằng cosine")
    if vectors.shape[1] != cfg.proj_dim:
        raise SystemExit(f"Chiều {vectors.shape[1]} ≠ proj_dim {cfg.proj_dim}")
    return ids, vectors, types, ckpt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--ratings", required=True, help="MovieLens u.data")
    ap.add_argument("--items", required=True, help="MovieLens u.item")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", default="19530")
    ap.add_argument("--collection", default=SANDBOX_COLLECTION)
    ap.add_argument("--manifest", help="ghi artifact manifest JSON (AI-09) ra file này")
    ap.add_argument("--top-k", type=int, default=10, help="k của truy vấn kiểm tra")
    args = ap.parse_args()
    check_target(args.collection)

    from pymilvus import Collection, connections, utility

    ids, vectors, types, ckpt = build_vectors(args.checkpoint, args.ratings, args.items)
    if args.manifest:
        with open(args.manifest, "w", encoding="utf-8") as f:
            json.dump(artifact_manifest(args.checkpoint, args.ratings, args.items, ids, types, ckpt), f, ensure_ascii=False, indent=1)
    n_user = types.count("user")
    print(f"checkpoint: {ckpt['metrics']}")
    print(f"vector: {len(ids)} ({n_user} user + {len(ids) - n_user} video), "
          f"{vectors.shape[1]}-d, ‖v‖=1")

    connections.connect(alias="default", host=args.host, port=args.port)
    if not utility.has_collection(args.collection):
        raise SystemExit(f"Chưa có {args.collection} — collection do Codex tạo (HC-04), không tự tạo")
    col = Collection(args.collection)

    # Xoá bản cũ trước khi nạp: PK là VARCHAR do mình đặt, `insert` lại cùng id sẽ tạo BẢN GHI
    # TRÙNG (Milvus không tự upsert khi insert), và truy vấn sau đó trộn vector cũ lẫn mới.
    # `load()` phải đứng TRƯỚC `delete()`: Milvus từ chối xoá trên collection chưa load
    # (code=101 collection not loaded).
    col.load()
    col.delete(expr=DELETE_EXPR)
    col.flush()
    col.insert([ids, vectors.tolist(), types])
    col.flush()
    col.load()
    # num_entities còn đếm row đã delete chưa compact → đếm row sống của namespace.
    live = col.query(expr=DELETE_EXPR, output_fields=["count(*)"], consistency_level="Strong")[0]["count(*)"]
    print(f"đã nạp {len(ids)} bản ghi; {live} row sống trong namespace ml100k_* của {args.collection}")
    if live != len(ids):
        raise SystemExit("Số row sống ≠ số vector vừa nạp — có bản ghi trùng/thiếu")

    # Truy vấn kiểm tra: 1 user → top-k video. Đây chính là DoD của T1.7d.
    # nprobe phải khớp giá trị production dùng. Lần đầu viết script này để nprobe=16 và nó PASS,
    # vì search chạy ngay sau insert khi segment chưa lập index (Milvus brute-force). Sau khi index
    # IVF_FLAT nlist=1024 hình thành, cùng truy vấn đó trả 0 hit — bài kiểm tra đã xác nhận nhầm
    # một đường đi không phải đường production.
    probe = ids[0]
    t0 = time.time()
    hits = col.search(
        data=[vectors[0].tolist()], anns_field="vector",
        param={"metric_type": "IP", "params": {"nprobe": 128}},
        limit=args.top_k, expr='type == "video"', output_fields=["id", "type"],
    )[0]
    ms = (time.time() - t0) * 1000

    print(f"\ntruy vấn {probe} → top-{args.top_k} video trong {ms:.0f} ms:")
    for h in hits:
        print(f"  {h.entity.get('id'):10} score={h.score:.4f}")
    if len(hits) != args.top_k:
        raise SystemExit(f"Chỉ trả {len(hits)}/{args.top_k} kết quả")
    if any(h.entity.get("type") != "video" for h in hits):
        raise SystemExit("Lọc type == 'video' không có tác dụng — kết quả lẫn vector user")
    if not all(-1.001 <= h.score <= 1.001 for h in hits):
        raise SystemExit("Score ngoài [-1,1]: vector không còn L2-norm")
    print(f"\nT1.7d: recommendation query OK ({ms:.0f} ms)")

    # AI-09: ANN (IVF_FLAT, nprobe=128 như service) phải khớp brute-force IP trên cùng vector.
    n_user = types.count("user")
    video_vecs, video_ids = vectors[n_user:], ids[n_user:]
    recalls = []
    for row in range(0, n_user, max(1, n_user // 50)):
        exact = {video_ids[j] for j in (video_vecs @ vectors[row]).topk(args.top_k).indices.tolist()}
        ann = col.search(data=[vectors[row].tolist()], anns_field="vector",
                         param={"metric_type": "IP", "params": {"nprobe": 128}},
                         limit=args.top_k, expr='type == "video"', output_fields=["id"])[0]
        recalls.append(len(exact & {h.entity.get("id") for h in ann}) / args.top_k)
    recall = sum(recalls) / len(recalls)
    print(f"ANN recall@{args.top_k} vs brute-force trên {len(recalls)} user: {recall:.4f}")
    if recall < 0.99:
        raise SystemExit("ANN lệch brute-force — kiểm nlist/nprobe")


if __name__ == "__main__":
    main()
