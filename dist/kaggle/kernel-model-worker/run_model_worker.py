"""AI-14 (D24): on-demand GPU model worker on Kaggle — app.worker_app behind a cloudflared quick tunnel.

Dataset `ai-model-worker-v1` (build_dataset.py): 6 active checkpoints (SHA = contract §1) + ai_core.zip + inference_service.zip.
No user data lives here: the facade (inference-service with MODEL_WORKER_URL) sends one request's bytes/vectors/text, the worker
returns labels/vectors/text and keeps nothing.

Limits: Kaggle session ≤12 h, weekly GPU quota, new tunnel URL every session (update MODEL_WORKER_URL each time).
Key: Kaggle secret MODEL_WORKER_KEY if attached to the notebook, else a fresh random key printed once in the private log.
Local dry run (CPU, no tunnel):  python run_model_worker.py --input D:/tmp/ai14_20261029/ds --device cpu --no-tunnel --minutes 0
"""
import argparse
import glob
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

MODELS = ("vit", "siamese", "asr_ctc", "highlight_fusion", "minigpt", "two_tower")
CLOUDFLARED = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def worker_key():
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("MODEL_WORKER_KEY"), "kaggle secret"
    except Exception:  # noqa: BLE001 — no secret attached / not on Kaggle
        return "wk-" + secrets.token_urlsafe(32), "generated"


def info(url, key, timeout=10):
    req = urllib.request.Request(url + "/info", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_info(url, key, seconds):
    deadline = time.time() + seconds
    while True:
        try:
            return info(url, key)
        except (urllib.error.URLError, OSError) as e:
            if time.time() > deadline:
                raise SystemExit(f"worker not reachable at {url}: {e}")
            time.sleep(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None)
    ap.add_argument("--scratch", default="/tmp/model-worker")
    ap.add_argument("--work", default="/kaggle/working")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--port", type=int, default=8002)
    ap.add_argument("--minutes", type=float, default=11.5 * 60)   # stop before Kaggle's 12 h session limit
    ap.add_argument("--no-tunnel", action="store_true")
    args = ap.parse_args()

    root = args.input or os.path.dirname(glob.glob("/kaggle/input/**/manifest.json", recursive=True)[0])
    manifest = json.load(open(os.path.join(root, "manifest.json")))
    # Kaggle may auto-extract uploaded zips: the code zips are then verified by package presence instead of hash.
    missing_zip = [p for p in manifest["sha256"] if p.endswith(".zip") and not os.path.exists(os.path.join(root, p))]
    bad = [p for p, h in manifest["sha256"].items() if p not in missing_zip and sha256(os.path.join(root, p)) != h]
    if bad:
        raise SystemExit(f"sha256 mismatch: {bad}")

    src = os.path.join(args.scratch, "src")
    for z in ("ai_core.zip", "inference_service.zip"):
        if z not in missing_zip:
            zipfile.ZipFile(os.path.join(root, z)).extractall(src)
    search = [src, os.path.dirname(root) if not args.input else root]
    core = next(os.path.dirname(os.path.dirname(p)) for d in search
                for p in glob.glob(f"{d}/**/ai_core/__init__.py", recursive=True) if os.path.isdir(os.path.join(os.path.dirname(p), "training")))
    service = next(os.path.dirname(os.path.dirname(p)) for d in search
                   for p in glob.glob(f"{d}/**/app/worker_app.py", recursive=True))
    ckpt = os.path.join(args.scratch, "checkpoints")
    for name in MODELS:
        os.makedirs(os.path.join(ckpt, name), exist_ok=True)
        shutil.copy2(os.path.join(root, f"ckpt_{name}.pt"), os.path.join(ckpt, name, "best.pt"))
    shutil.copy2(os.path.join(root, "ckpt_minigpt_bpe_vocab.json"), os.path.join(ckpt, "minigpt", "bpe_vocab.json"))
    for mod, pkg in (("fastapi", "fastapi"), ("uvicorn", "uvicorn"), ("soundfile", "soundfile")):
        try:
            __import__(mod)
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=True)

    key, key_source = worker_key()
    env = dict(os.environ, MODEL_WORKER_KEY=key, CHECKPOINT_DIR=ckpt, INFER_DEVICE=args.device, FORCE_STUB="0",
               PYTHONPATH=os.pathsep.join([service, core]), PYTHONUTF8="1")
    env.pop("MODEL_WORKER_URL", None)
    log = open(os.path.join(args.scratch, "worker.log"), "w")
    worker = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.worker_app:app", "--host", "127.0.0.1", "--port", str(args.port)],
                              cwd=service, env=env, stdout=log, stderr=subprocess.STDOUT)
    local = f"http://127.0.0.1:{args.port}"
    status = wait_info(local, key, 600)
    print("worker ready:", json.dumps(status), flush=True)
    if status["stub_mode"] or sorted(status["models_loaded"]) != sorted(MODELS):
        raise SystemExit("worker did not load all 6 checkpoints")

    url, tunnel = local, None
    if not args.no_tunnel:
        binary = os.path.join(args.scratch, "cloudflared")
        urllib.request.urlretrieve(CLOUDFLARED, binary)
        os.chmod(binary, 0o755)
        tunnel_log = os.path.join(args.scratch, "cloudflared.log")
        tunnel = subprocess.Popen([binary, "tunnel", "--no-autoupdate", "--url", local],
                                  stdout=open(tunnel_log, "w"), stderr=subprocess.STDOUT)
        found = None
        for _ in range(60):
            time.sleep(2)
            found = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open(tunnel_log).read())
            if found or tunnel.poll() is not None:
                break
        if not found:
            raise SystemExit("cloudflared gave no tunnel URL: " + open(tunnel_log).read()[-2000:])
        url = found.group(0)
        wait_info(url, key, 120)                      # the public name needs a few seconds to resolve

    print("=" * 72)
    print(f"MODEL_WORKER_URL={url}")
    print(f"MODEL_WORKER_KEY={key}" if key_source == "generated" else "MODEL_WORKER_KEY=<Kaggle secret MODEL_WORKER_KEY>")
    print(f"device={status['device']} models={','.join(status['models_loaded'])} — URL changes every session")
    print("=" * 72, flush=True)
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "session.json"), "w") as f:   # no key, no request data
        json.dump({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "url": url, "key_source": key_source,
                   "device": status["device"], "models_loaded": status["models_loaded"], "manifest_ok": True}, f, indent=1)

    deadline = time.time() + args.minutes * 60
    try:
        while time.time() < deadline and worker.poll() is None and (tunnel is None or tunnel.poll() is None):
            time.sleep(30)
    finally:
        for proc in (tunnel, worker):
            if proc is not None:
                proc.terminate()
        log.close()
        shutil.copy2(os.path.join(args.scratch, "worker.log"), os.path.join(args.work, "worker.log"))
    print("session ended", flush=True)


if __name__ == "__main__":
    main()
