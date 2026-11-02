"""AI-22 (HO-04): prove a running AI container = git source at its label revision + active checkpoints + host recipe.

  PYTHONUTF8=1 PYTHONPATH="ai-core;inference-service" .venv/Scripts/python coordination/claude/evidence/AI-22_2026-11-02/parity.py \
      <container> <base_url> <features.pt> out.json        (run from repo root; key from env INFERENCE_LIVE_KEY)
1. image label org.opencontainers.image.revision set, HEAD has the same app/ + ai_core/; 2. every file of app/ + ai_core/ in the image == git blob at that revision;
3. mounted checkpoints == contract §1 SHA (+ recipe members == host files); 4. /v1/highlight on real-length features ==
   in-process run_highlight on the host (same request, response rounding 0.1) — the recipe really runs in the container.
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path.cwd()
sys.path.insert(0, str(ROOT / "dist/kaggle/kernel-model-worker"))
from build_dataset import MODELS, contract_sha, sha  # noqa: E402

container, base_url, features_path, out_path = sys.argv[1:5]
KEY = os.environ["INFERENCE_LIVE_KEY"]


def sh(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8").stdout


def in_container(code):
    return json.loads(sh("docker", "exec", container, "python", "-c", code))


result = {"container": container, "image": sh("docker", "inspect", container, "--format", "{{.Config.Image}}").strip()}
rev = sh("docker", "inspect", container, "--format", '{{index .Config.Labels "org.opencontainers.image.revision"}}').strip()
result["revision"] = {"label": rev, "head": sh("git", "rev-parse", "HEAD").strip(),
                      "head_source_changed": sh("git", "diff", "--name-only", rev, "HEAD", "--", "inference-service/app", "ai-core/ai_core").split()}

# 2. source: git blob ids (sha1 "blob <len>\0<bytes>") inside the image vs the tree at the label revision
image_blobs = in_container(r"""
import hashlib, json, pathlib
out = {}
for base, prefix in (("/srv/inference-service/app", "inference-service/app"), ("/srv/ai-core/ai_core", "ai-core/ai_core")):
    for p in pathlib.Path(base).rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            b = p.read_bytes().replace(b"\r\n", b"\n")   # build context = Windows checkout (core.autocrlf=true); git blobs are LF
            out[prefix + "/" + p.relative_to(base).as_posix()] = hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()
print(json.dumps(out))
""")
git_blobs = {}
for line in sh("git", "ls-tree", "-r", rev, "--", "inference-service/app", "ai-core/ai_core").splitlines():
    meta, path = line.split("\t", 1)
    if not path.startswith("ai-core/ai_core/tests/"):          # excluded by .dockerignore
        git_blobs[path] = meta.split()[2]
result["source"] = {"files": len(git_blobs),
                    "mismatch": sorted(p for p in git_blobs if p in image_blobs and image_blobs[p] != git_blobs[p]),
                    "missing_in_image": sorted(set(git_blobs) - set(image_blobs)),
                    "extra_in_image": sorted(set(image_blobs) - set(git_blobs))}

# 3. checkpoints as mounted in the container
recipe = json.loads((ROOT / "ai-core/checkpoints/highlight_fusion/postproc.json").read_text(encoding="utf-8"))
files = [f"{m}/best.pt" for m in MODELS] + ["minigpt/bpe_vocab.json", "highlight_fusion/postproc.json"] + \
        [f"highlight_fusion/{r}" for r in recipe.get("extra_members", [])]
mounted = in_container(f"""
import hashlib, json
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
print(json.dumps({{f: sha("/srv/ai-core/checkpoints/" + f) for f in {files!r}}}))
""")
want = contract_sha(ROOT)
result["checkpoints"] = {f: {"container": mounted[f], "host": sha(ROOT / "ai-core/checkpoints" / f),
                             "contract": want[f.split("/")[0]] if f.endswith("/best.pt") else None} for f in files}
result["checkpoints_ok"] = all(c["container"] == c["host"] and c["contract"] in (None, c["container"]) for c in result["checkpoints"].values())

# 4. behaviour: same real-length request, container HTTP vs host in-process service
import torch  # noqa: E402
from app import services  # noqa: E402
from app.registry import registry  # noqa: E402
from app.schemas import HighlightRequest  # noqa: E402

registry.load_all()
behaviour = []
for h in torch.load(features_path, map_location="cpu", weights_only=False)["test"][:2]:
    req = {"video_id": "vid_ai22parity", "features": {"vision_embeddings": h["vision"].tolist(), "audio_spectrogram_features": h["audio"].tolist()}}
    r = urllib.request.Request(base_url + "/v1/highlight/completions", data=json.dumps(req).encode(), method="POST",
                               headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(r, timeout=600) as resp:
        remote = json.loads(resp.read())
    local = services.run_highlight(HighlightRequest(**req)).model_dump()
    ds = [abs(a["score"] - b["score"]) for a, b in zip(remote["timeline_scores"], local["timeline_scores"])]
    behaviour.append({"video": h["name"], "seconds": len(ds), "max_abs_score_diff": round(max(ds), 3),
                      "clip_threshold": [remote["clip_threshold"], local["clip_threshold"]],
                      "clips_container": [[c["start_time"], c["end_time"]] for c in remote["recommended_clips"]],
                      "clips_host": [[c["start_time"], c["end_time"]] for c in local["recommended_clips"]]})
result["behaviour"] = behaviour
result["torch"] = {"host": torch.__version__, "container": in_container("import json, torch; print(json.dumps(torch.__version__))")}
result["PASS"] = bool(rev and not result["revision"]["head_source_changed"] and not any(result["source"][k] for k in ("mismatch", "missing_in_image", "extra_in_image"))
                      and result["checkpoints_ok"] and all(b["max_abs_score_diff"] <= 0.2 and b["clips_container"] == b["clips_host"]
                                                           and b["clip_threshold"][0] == b["clip_threshold"][1] for b in behaviour))
pathlib.Path(out_path).write_text(json.dumps(result, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "checkpoints"}, indent=1))
print("PARITY", "PASS" if result["PASS"] else "FAIL")
