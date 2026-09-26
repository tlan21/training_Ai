"""VIVOS → manifest ASR, GIỮ NGUYÊN split train/test chính thức (T1.4c/d).

Dùng:
  python -m ai_core.scripts.prepare_vivos \
      --root data/raw/vivos/vivos --manifest data/manifests/vivos.json

Vì sao không dùng `build_asr_manifest.py`: script đó nhận thư mục audio phẳng + transcript JSON rồi
chia **ngẫu nhiên 80/10/10** bằng `split_by_group`. VIVOS có split train/test do tác giả định sẵn,
và DoD T1.4d đòi chấm WER/CER **trên VIVOS test** — chia ngẫu nhiên là trộn test chính thức vào
train, số WER báo cáo sẽ không so được với bất kỳ công bố nào dùng cùng bộ dữ liệu.

Val cắt từ train **theo NGƯỜI NÓI**, không theo câu. Cắt theo câu thì cùng một giọng có mặt ở cả
train lẫn val, early-stop nhìn val sẽ lạc quan vì model đã quen giọng đó — trong khi test là 19
người nói hoàn toàn khác.

Transcript giữ nguyên chữ hoa: đo trên dữ liệu thật, VIVOS chỉ dùng chữ hoa nên `.lower()` không
giảm được ký tự nào (92 ký tự cả trước lẫn sau) — thêm một phép biến đổi vô ích là thêm một chỗ
lệch giữa train và inference.
"""

import argparse
import os
import random

from ..data import ManifestItem, save_manifest


def read_prompts(root: str, split: str) -> list[tuple[str, str, str]]:
    """→ [(utt_id, speaker, transcript)] từ <root>/<split>/prompts.txt."""
    out = []
    path = os.path.join(root, split, "prompts.txt")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            utt, _, text = line.partition(" ")
            text = text.strip()
            if text:
                out.append((utt, utt.split("_")[0], text))
    if not out:
        raise SystemExit(f"{path} rỗng hoặc sai định dạng 'UTTID transcript'")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="thư mục vivos/ (chứa train/ và test/)")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--val-speakers", type=int, default=5,
                    help="số người nói tách khỏi train làm val (cắt theo NGƯỜI, không theo câu)")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    train_rows = read_prompts(args.root, "train")
    test_rows = read_prompts(args.root, "test")

    speakers = sorted({spk for _, spk, _ in train_rows})
    if args.val_speakers >= len(speakers):
        raise SystemExit(f"--val-speakers {args.val_speakers} ≥ {len(speakers)} người nói của train")
    val_spk = set(random.Random(args.seed).sample(speakers, args.val_speakers))

    items, missing = [], []
    for split_dir, rows in (("train", train_rows), ("test", test_rows)):
        for utt, spk, text in rows:
            wav = os.path.join(args.root, split_dir, "waves", spk, f"{utt}.wav").replace(os.sep, "/")
            if not os.path.exists(wav):
                missing.append(wav)
                continue
            split = "test" if split_dir == "test" else ("val" if spk in val_spk else "train")
            items.append(ManifestItem(
                path=wav, label="vi", split=split, group=spk,
                extra={"transcript": text, "speaker": spk}))

    if missing:
        raise SystemExit(f"{len(missing)} wav có trong prompts.txt nhưng không tồn tại, vd {missing[0]}")

    per_split: dict[str, int] = {}
    spk_of: dict[str, set] = {}
    chars: set[str] = set()
    for it in items:
        per_split[it.split] = per_split.get(it.split, 0) + 1
        spk_of.setdefault(it.split, set()).add(it.group)
        chars |= set(it.extra["transcript"])
    for split in ("train", "val", "test"):
        if not per_split.get(split):
            raise SystemExit(f"Split '{split}' rỗng — early-stop/eval sẽ im lặng vô hiệu")
    leak = ((spk_of["train"] & spk_of["val"]) | (spk_of["train"] & spk_of["test"])
            | (spk_of["val"] & spk_of["test"]))
    if leak:
        raise SystemExit(f"Người nói xuất hiện ở nhiều split: {sorted(leak)}")

    save_manifest(args.manifest, items,
                  meta={"task": "asr_vivos", "seed": args.seed, "sr": 16000,
                        "val_speakers": sorted(val_spk), "n_chars": len(chars)})
    print(f"{len(items):,} câu → {args.manifest}")
    for split in ("train", "val", "test"):
        print(f"  {split:5} {per_split[split]:6,} câu | {len(spk_of[split]):2} người nói")
    print(f"ký tự khác nhau: {len(chars)} (vocab CTC = {len(chars) + 1} kèm blank)")


if __name__ == "__main__":
    main()
