"""Extract one ViT embedding per manifest frame and group it by video."""

import argparse
import os

import torch

from .. import build_model
from ..config import ModelConfig
from ..data import load_manifest
from ..training.checkpoint import load_checkpoint


def _load_image(path: str, size: int) -> torch.Tensor:
    import numpy as np
    from PIL import Image

    image = Image.open(path).convert("RGB").resize((size, size))
    return torch.from_numpy(np.asarray(image)).float().div(255).permute(2, 0, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=32,
                    help="1 ảnh/lần trên CPU quá chậm với 111k frame; batch nhanh hơn ~3×")
    ap.add_argument("--threads", type=int, default=0,
                    help="giới hạn thread torch; 0 = mặc định. Đặt khi có process torch khác chạy "
                         "song song — tranh thread MKL/OMP trên Windows từng gây segfault")
    ap.add_argument("--device", default="auto", help="cuda | cpu | auto")
    args = ap.parse_args()

    if args.threads:
        torch.set_num_threads(args.threads)
    # Bản cũ KHÔNG chuyển model sang GPU: chạy trên Kaggle T4 vẫn là CPU, chỉ chậm hơn chứ không
    # báo gì. 443k frame là ~5 giờ CPU so với ~15 phút GPU.
    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    print(f"device: {device}", flush=True)

    ckpt = load_checkpoint(args.checkpoint)
    cfg = ModelConfig(**ckpt["config"])
    model = build_model(ckpt["config"].get("name", "vit"), cfg).eval()
    model.load_state_dict(ckpt["state_dict"])      # bản cũ QUÊN nạp → embedding từ trọng số random
    model.to(device)

    # Lấy embedding của BACKBONE (d_model), không phải đầu ra projection head:
    #  - highlight_dataset đòi (n_sec, 256) = d_model, còn SiameseViT.encode() trả proj_dim=128.
    #  - Biểu diễn TRƯỚC projection head transfer tốt hơn cho downstream (kết quả chuẩn của
    #    self-supervised contrastive) → vừa đúng spec vừa đúng phương pháp.
    backbone = model.backbone if hasattr(model, "backbone") else model

    items = [it for it in load_manifest(args.manifest) if it.group]
    if not items:
        raise SystemExit(f"Manifest {args.manifest} không có item nào có group")

    by_group: dict[str, list] = {}
    for it in items:
        by_group.setdefault(it.group, []).append(it)

    # Lưu TĂNG DẦN sau mỗi group, và bỏ qua group đã có. 111k frame mất ~80 phút CPU; một lần
    # segfault (đã gặp: chạy song song 2 process PyTorch trên Windows) làm mất trắng cả lô nếu
    # chỉ torch.save một lần ở cuối.
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    output = torch.load(args.out, map_location="cpu", weights_only=False) \
        if os.path.exists(args.out) else {}
    if output:
        print(f"tiếp tục: đã có {len(output)} group trong {args.out}", flush=True)

    with torch.no_grad():
        for gi, (group, gitems) in enumerate(sorted(by_group.items()), 1):
            if group in output:
                continue
            gitems = sorted(gitems, key=lambda x: int(x.extra.get("sec", 0)))
            embs = []
            for start in range(0, len(gitems), args.batch_size):
                chunk = gitems[start:start + args.batch_size]
                batch = torch.stack([_load_image(it.path, cfg.img_size) for it in chunk]).to(device)
                _, emb = backbone(batch, return_embedding=True)
                embs.append(emb.float().cpu())
            output[group] = torch.cat(embs)
            torch.save(output, args.out)          # chốt sau từng group
            print(f"[{gi}/{len(by_group)}] {group}: {tuple(output[group].shape)}", flush=True)

    print(f"embeddings: {len(output)} video → {args.out}")


if __name__ == "__main__":
    main()
