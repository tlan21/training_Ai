"""Đóng gói frame của một manifest thành JPEG trong 1 file zip để đưa lên Kaggle (T1.3a).

Dùng:
  python -m ai_core.scripts.export_vit_jpg --manifest D:/.../manifests/vit_4cls.json \
      --zip D:/.../kaggle/vit-4cls-jpg/vit_4cls_jpg.zip --out-manifest D:/.../kaggle/vit-4cls-jpg/vit_4cls_jpg.json

PNG 426×240 ≈ 108 KB/frame → 64k frame ≈ 7 GB; JPEG q95 ≈ 34 KB → ≈ 2,2 GB. Mọi lớp và cả hai
baseline đều đọc cùng bản JPEG, nên mức nén không nghiêng về lớp nào.

Ghi thẳng vào zip (ZIP_STORED — JPEG không nén thêm được) thay vì ra thư mục rồi mới zip: ổ D
không đủ chỗ cho hai bản 2,2 GB. Đường dẫn trong manifest là tương đối `<group>/<file>.jpg`;
kernel ghép với thư mục Kaggle đã giải nén.
"""

import argparse
import io
import json
import os
import zipfile

from PIL import Image

from ..data import ManifestItem, load_manifest, save_manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--zip", required=True)
    ap.add_argument("--out-manifest", required=True)
    ap.add_argument("--quality", type=int, default=95)
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        meta = json.load(f)["meta"]
    items = load_manifest(args.manifest)
    root = os.path.splitext(os.path.basename(args.zip))[0]
    os.makedirs(os.path.dirname(args.zip) or ".", exist_ok=True)
    tmp = args.zip + ".part"                 # zip dở (job bị cắt) không được mang tên file thật
    out = []
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:
        for n, it in enumerate(items, 1):
            rel = f"{it.group}/{it.group}_s{it.extra['sec']:05d}.jpg"
            buf = io.BytesIO()
            Image.open(it.path).convert("RGB").save(buf, "JPEG", quality=args.quality)
            z.writestr(f"{root}/{rel}", buf.getvalue())
            out.append(ManifestItem(path=rel, label=it.label, split=it.split, group=it.group,
                                    extra={"sec": it.extra["sec"],
                                           "src_checksum": it.extra.get("checksum")}))
            if n % 5000 == 0:
                print(f"{n}/{len(items)}", flush=True)
    if len({o.path for o in out}) != len(out):
        raise SystemExit("trùng đường dẫn (group, sec) — manifest nguồn có frame lặp")
    os.replace(tmp, args.zip)
    save_manifest(args.out_manifest, out, meta={**meta, "jpeg_quality": args.quality,
                                                 "source_manifest": os.path.basename(args.manifest)})
    print(f"{len(out)} frame → {args.zip} ({os.path.getsize(args.zip) / 1e9:.2f} GB)")


if __name__ == "__main__":
    main()
