"""Build the private Kaggle dataset `ai-model-worker-v1` (AI-14, D24): 6 active checkpoints + worker code. No user data.

  .venv/Scripts/python dist/kaggle/kernel-model-worker/build_dataset.py D:/tmp/ai14_20261029/ds   (run from repo root)
Refuses to build unless every checkpoint matches the SHA256 table in coordination/claude/api/AI_API_CONTRACT.md §1.
"""
import hashlib
import json
import pathlib
import re
import shutil
import sys
import zipfile

MODELS = ("vit", "siamese", "asr_ctc", "highlight_fusion", "minigpt", "two_tower")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def contract_sha(root):
    text = (root / "coordination/claude/api/AI_API_CONTRACT.md").read_text(encoding="utf-8")
    found = dict(re.findall(r"^\| `(\w+)` \|.*\| `([0-9a-f]{64})` \|$", text, re.M))
    missing = [m for m in MODELS if m not in found]
    if missing:
        raise SystemExit(f"contract §1 has no SHA for {missing}")
    return {m: found[m] for m in MODELS}


def zip_tree(out, base, sub):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in (base / sub).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, p.relative_to(base.parent).as_posix())


def main(dst):
    root, dst = pathlib.Path.cwd(), pathlib.Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    # Flat layout: Kaggle auto-extracts zips / reshapes folders, so the kernel rebuilds checkpoints/<model>/best.pt itself.
    for name, want in contract_sha(root).items():
        src = root / "ai-core/checkpoints" / name / "best.pt"
        if sha(src) != want:
            raise SystemExit(f"{name}: checkpoint is not the active one (contract §1)")
        shutil.copy2(src, dst / f"ckpt_{name}.pt")
    shutil.copy2(root / "ai-core/checkpoints/minigpt/bpe_vocab.json", dst / "ckpt_minigpt_bpe_vocab.json")
    zip_tree(dst / "ai_core.zip", root / "ai-core", "ai_core")
    zip_tree(dst / "inference_service.zip", root / "inference-service", "app")
    files = sorted(p for p in dst.iterdir() if p.is_file() and p.name not in ("manifest.json", "dataset-metadata.json"))
    manifest = {"purpose": "AI-14 remote model worker (D24)", "sha256": {p.name: sha(p) for p in files}}
    (dst / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (dst / "dataset-metadata.json").write_text(json.dumps(
        {"title": "ai-model-worker-v1", "id": "traininghighlight/ai-model-worker-v1", "isPrivate": True, "licenses": [{"name": "other"}]}, indent=1))
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
