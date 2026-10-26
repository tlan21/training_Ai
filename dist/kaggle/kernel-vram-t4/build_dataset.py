"""Build the private Kaggle dataset `ai-vram-t4-v1` for AI-04 (run from repo root; output outside the repo).

  .venv/Scripts/python dist/kaggle/kernel-vram-t4/build_dataset.py D:/tmp/ai04_vram/ds
Refuses to build unless every checkpoint matches the active SHA256 in the AI API contract.
"""
import hashlib
import json
import pathlib
import shutil
import sys
import zipfile

ACTIVE = {  # coordination/claude/api/AI_API_CONTRACT.md §1
    "vit": "192d90e4fad893cec1542c5630715cc3bc22197e8cd8ba22a6fb84a64a88ad7f",
    "siamese": "b4ded465b8eea134a01652811008656b9e0c59716431136bb161216310bbcebb",
    "asr_ctc": "8f87986781cfb3d4716691f2051e5798187693e2452f9f41b28ca4a753ea5531",
    "highlight_fusion": "becbd378ca237c6992867ca5309663d3c1c142a99b40da57f9a0fb652489b49c",
    "minigpt": "cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac",
    "two_tower": "f28c37943ec499d168f43b5281879273af326a97ee47e571100c93dee0c91695",
}
MEDIA = pathlib.Path("D:/tmp/ai01_20261026/media")     # 3 frames + 10 s WAV cut from a CC video already used in AI-01


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def zip_tree(out, base, sub):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in (base / sub).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, p.relative_to(base.parent).as_posix())


def main(dst):
    root, dst = pathlib.Path.cwd(), pathlib.Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    # Flat layout: Kaggle auto-extracts zips / reshapes folders, so the kernel rebuilds checkpoints/<model>/best.pt itself.
    for name, want in ACTIVE.items():
        src = root / "ai-core/checkpoints" / name / "best.pt"
        if sha(src) != want:
            raise SystemExit(f"{name}: checkpoint is not the active one")
        shutil.copy2(src, dst / f"ckpt_{name}.pt")
    shutil.copy2(root / "ai-core/checkpoints/minigpt/bpe_vocab.json", dst / "ckpt_minigpt_bpe_vocab.json")
    zip_tree(dst / "ai_core.zip", root / "ai-core", "ai_core")
    zip_tree(dst / "inference_service.zip", root / "inference-service", "app")
    for p in MEDIA.iterdir():
        shutil.copy2(p, dst / f"media_{p.name}")
    files = sorted(p for p in dst.iterdir() if p.is_file() and p.name not in ("manifest.json", "dataset-metadata.json"))
    manifest = {"purpose": "AI-04 PRELIMINARY_T4 VRAM", "sha256": {p.relative_to(dst).as_posix(): sha(p) for p in files}}
    (dst / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (dst / "dataset-metadata.json").write_text(json.dumps(
        {"title": "ai-vram-t4-v1", "id": "traininghighlight/ai-vram-t4-v1", "isPrivate": True, "licenses": [{"name": "other"}]}, indent=1))
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
