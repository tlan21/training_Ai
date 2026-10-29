"""Remote model worker (D24): GET /info + POST /ops/{op} behind its own Bearer MODEL_WORKER_KEY. No MinIO/Milvus.

The facade (app.main with MODEL_WORKER_URL) is the only client; it keeps the public API, auth and data I/O.
  MODEL_WORKER_KEY=<random ≥24 chars> CHECKPOINT_DIR=... python -m uvicorn app.worker_app:app --host 127.0.0.1 --port 8002
"""

import base64
import binascii
import hmac
import inspect
import os
import threading
from contextlib import asynccontextmanager

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from . import worker
from .registry import registry

_BINARY = {"images", "pcm"}
_lock = threading.Lock()  # ponytail: one op at a time per worker (one GPU), same as the facade's GPU queue


def _key() -> str:
    return os.environ.get("MODEL_WORKER_KEY", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(_key()) < 24 or _key() == "sk-local-dev-key":
        raise RuntimeError("MODEL_WORKER_KEY: set a random key (≥24 chars), never sk-local-dev-key")
    registry.load_all()
    if registry.stub_mode:
        raise RuntimeError(f"Model worker requires all 6 checkpoints: {registry.load_error}")
    yield


app = FastAPI(title="AI Model Worker", version="1.0.0", lifespan=lifespan)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(HTTPException)
async def _http_exc(request, exc: HTTPException):
    return _error(exc.status_code, "UNAUTHORIZED" if exc.status_code == 401 else "HTTP_ERROR", str(exc.detail))


def _auth(authorization: str = Header(default="")) -> None:
    if not hmac.compare_digest(authorization.encode(), f"Bearer {_key()}".encode()):
        raise HTTPException(401, "Invalid or missing model worker key")


@app.get("/info", dependencies=[Depends(_auth)])
def info():
    return worker.info()


@app.post("/ops/{op}", dependencies=[Depends(_auth)])
def run(op: str, body: dict = Body(...)):
    fn = worker.OPS.get(op)
    if fn is None:
        return _error(404, "NOT_FOUND", f"unknown op {op}")
    try:
        kwargs = {k: ([base64.b64decode(x, validate=True) for x in v] if isinstance(v, list) else base64.b64decode(v, validate=True))
                  if k in _BINARY else v for k, v in body.items()}
        inspect.signature(fn).bind(**kwargs)
    except (binascii.Error, TypeError, ValueError) as e:
        return _error(422, "VALIDATION_ERROR", f"{type(e).__name__}: {e}")
    try:
        with _lock:
            return {"result": fn(**kwargs)}
    except worker.InvalidInput as e:
        return _error(422, "VALIDATION_ERROR", str(e))
    except Exception as e:  # noqa: BLE001 — the facade decides degraded vs fallback
        return _error(500, "MODEL_ERROR", f"{type(e).__name__}: {e}")
