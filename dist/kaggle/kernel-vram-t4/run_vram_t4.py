"""AI-04 (PRELIMINARY_T4): VRAM of the 6 active checkpoints in the real inference-service code, sequential requests.

Kaggle: dataset `ai-vram-t4-v1` (6 best.pt + bpe_vocab, ai_core.zip, inference_service.zip, media, manifest.json).
Local dry-run on CPU:  python run_vram_t4.py --input D:/tmp/ai04_vram/ds --work D:/tmp/ai04_vram/work --device cpu

Measures through `app.services` (the same functions the HTTP endpoints call), not HTTP: Milvus/MinIO do not exist on
Kaggle, so search = Siamese encode only and recommendation (Milvus-only, no GPU work) is skipped. Not an RTX 3060 result.
"""
import argparse
import base64
import glob
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import types
import zipfile


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None)
    ap.add_argument("--work", default="/kaggle/working")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--rounds", type=int, default=4)        # 4 rounds × 5 request kinds = 20 sequential requests
    ap.add_argument("--scratch", default="/tmp/vram")
    ap.add_argument("--frames", type=int, default=32)
    ap.add_argument("--audio-seconds", type=float, default=25.0)
    args = ap.parse_args()
    root = args.input or os.path.dirname(glob.glob("/kaggle/input/**/manifest.json", recursive=True)[0])
    manifest = json.load(open(os.path.join(root, "manifest.json")))
    # Kaggle may auto-extract uploaded zips: the code zips are then verified by package presence instead of hash.
    missing_zip = [p for p in manifest["sha256"] if p.endswith(".zip") and not os.path.exists(os.path.join(root, p))]
    bad = [p for p, h in manifest["sha256"].items() if p not in missing_zip and sha256(os.path.join(root, p)) != h]
    if bad:
        raise SystemExit(f"sha256 mismatch: {bad}")

    scratch = args.scratch                                     # code/checkpoints/temp audio: never in the Kaggle output
    os.makedirs(scratch, exist_ok=True)
    src = os.path.join(scratch, "src")
    for z in ("ai_core.zip", "inference_service.zip"):
        if z not in missing_zip:
            zipfile.ZipFile(os.path.join(root, z)).extractall(src)
    search = [src, os.path.dirname(root) if not args.input else root]
    core = next(os.path.dirname(os.path.dirname(p)) for d in search
                for p in glob.glob(f"{d}/**/ai_core/__init__.py", recursive=True) if os.path.isdir(os.path.join(os.path.dirname(p), "training")))
    service = next(os.path.dirname(os.path.dirname(p)) for d in search
                   for p in glob.glob(f"{d}/**/app/registry.py", recursive=True))
    ckpt = os.path.join(scratch, "checkpoints")
    for name in ("vit", "siamese", "asr_ctc", "highlight_fusion", "minigpt", "two_tower"):
        os.makedirs(os.path.join(ckpt, name), exist_ok=True)
        shutil.copy2(os.path.join(root, f"ckpt_{name}.pt"), os.path.join(ckpt, name, "best.pt"))
    shutil.copy2(os.path.join(root, "ckpt_minigpt_bpe_vocab.json"), os.path.join(ckpt, "minigpt", "bpe_vocab.json"))
    for mod, pkg in (("fastapi", "fastapi"), ("soundfile", "soundfile")):
        try:
            __import__(mod)
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=True)
    try:
        import minio  # noqa: F401
    except ImportError:  # index_frames imports it first; with data-URI keyframes and no video_id it returns before use
        sys.modules["minio"] = types.SimpleNamespace(Minio=None)

    os.environ.update(CHECKPOINT_DIR=ckpt, INFER_DEVICE=args.device, FORCE_STUB="0", AI_SERVICE_KEY="sk-local-vram")
    sys.path[:0] = [service, core]
    import torch
    cuda = args.device == "cuda"
    if cuda and not torch.cuda.is_available():
        raise SystemExit("CUDA not available")

    def mem():
        if not cuda:
            return {}
        torch.cuda.synchronize()
        return {"allocated_mib": torch.cuda.memory_allocated() / 2**20, "reserved_mib": torch.cuda.memory_reserved() / 2**20,
                "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20, "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20}

    env = {"python": platform.python_version(), "torch": torch.__version__, "device": args.device, "platform": platform.platform()}
    if cuda:
        env |= {"gpu": torch.cuda.get_device_name(0), "cuda": torch.version.cuda,
                "total_mib": torch.cuda.get_device_properties(0).total_memory / 2**20,
                "driver": subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                         capture_output=True, text=True).stdout.strip()}
        torch.cuda.reset_peak_memory_stats()

    from app.registry import registry
    from app import schemas, services, visual_index
    t = time.perf_counter()
    registry.load_all()
    if registry.stub_mode:
        raise SystemExit(f"checkpoints not loaded: {registry.load_error}")
    load = {"seconds": time.perf_counter() - t, "dtype": str(registry.model_dtype), "models": sorted(registry.loaded), **mem()}

    real = ["data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode() for p in sorted(glob.glob(f"{root}/media_*.jpg"))]
    frames = [real[i % len(real)] for i in range(args.frames)]     # ≥ 2 full ViT/Siamese batches of 16
    import soundfile as sf
    from ai_core.audio.features import audio_features_per_second
    clip, sr = sf.read(os.path.join(root, "media_clip.wav"), dtype="float32")
    signal = torch.from_numpy(clip).repeat(int(args.audio_seconds * sr // len(clip)) + 1)[: int(args.audio_seconds * sr)].numpy()
    wav = os.path.join(scratch, "asr_input.wav")                  # ≥ one full 20 s ASR window
    sf.write(wav, signal, sr)
    audio = audio_features_per_second(torch.from_numpy(clip), sr).tolist()
    vis = services.run_vision(schemas.VisionRequest(keyframes=frames)).embeddings_256
    n = 120                                                       # one full Fusion window (worst case per call)
    feats = schemas.HighlightFeatures(vision_embeddings=[vis[i % len(vis)] for i in range(n)],
                                      audio_spectrogram_features=[audio[i % len(audio)] for i in range(n)])
    prompt = " ".join(["Đội tuyển bóng đá quốc gia đã có buổi tập đầu tiên chuẩn bị cho vòng loại tại Hà Nội."] * 40)  # forces map-reduce
    kinds = {
        "vision": lambda: services.run_vision(schemas.VisionRequest(keyframes=frames)),
        "asr": lambda: services.run_asr(schemas.ASRRequest(audio_url=wav, language="vi")),
        "highlight_120s": lambda: services.run_highlight(schemas.HighlightRequest(video_id="vid_vram", features=feats)),
        "completions_long": lambda: services.run_completion(schemas.CompletionRequest(prompt=prompt, max_tokens=96, temperature=0)),
        "siamese_encode": lambda: visual_index.encode([services._load_keyframe(f) for f in frames]),
    }
    requests = []
    for r in range(args.rounds):
        for name, fn in kinds.items():
            if cuda:
                torch.cuda.reset_peak_memory_stats()
            t = time.perf_counter()
            try:
                fn()
                ok, err = True, None
            except Exception as e:  # noqa: BLE001 — record, keep measuring the rest
                ok, err = False, f"{type(e).__name__}: {e}"
            requests.append({"round": r, "kind": name, "ok": ok, "error": err, "ms": (time.perf_counter() - t) * 1000, **mem()})
    peak = max((q.get("peak_reserved_mib", 0) for q in requests), default=0)
    inputs = {"vision_frames": len(frames), "asr_seconds": args.audio_seconds, "highlight_seconds": n,
              "completion_prompt_chars": len(prompt), "completion_max_tokens": 96}
    report = {"label": "PRELIMINARY_T4", "env": env, "inputs": inputs, "manifest_sha256": manifest["sha256"], "load": load, "requests": requests,
              "summary": {"n_requests": len(requests), "n_ok": sum(q["ok"] for q in requests),
                          "peak_reserved_mib_any_request": peak,
                          "peak_allocated_mib_any_request": max((q.get("peak_allocated_mib", 0) for q in requests), default=0),
                          "tail_allocated_mib": requests[-1].get("allocated_mib"),
                          "under_4gib": peak <= 4096 if cuda else None}}
    out = os.path.join(args.work, "vram_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps(report["summary"], ensure_ascii=False))
    print("load", json.dumps(load, ensure_ascii=False))
    for q in requests:
        print(q["round"], q["kind"], q["ok"], round(q["ms"]), {k: round(v, 1) for k, v in q.items() if k.endswith("_mib")}, q["error"] or "")


if __name__ == "__main__":
    main()
