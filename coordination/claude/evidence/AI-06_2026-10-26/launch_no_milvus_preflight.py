"""AI-06 launcher (tạm, không commit): uvicorn thật + checkpoint thật, CHỈ bỏ lần gọi Milvus preflight trong lifespan.
Milvus thuộc stack Codex và đang tắt. Các lần gọi visual_index.collection() sau đó (search) vẫn đi đường thật → 503."""
import os
import sys

ROOT = "E:/traning_ai"
os.chdir(f"{ROOT}/inference-service")
sys.path[:0] = [f"{ROOT}/inference-service", f"{ROOT}/ai-core"]

from app import visual_index  # noqa: E402

_orig = visual_index.collection
_calls = {"n": 0}


def _skip_first_call():
    _calls["n"] += 1
    if _calls["n"] == 1:
        print("[AI-06 launcher] skipped Milvus preflight (call #1 only)", flush=True)
        return None
    return _orig()


visual_index.collection = _skip_first_call

import uvicorn  # noqa: E402
from app.main import app  # noqa: E402

uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8011)
