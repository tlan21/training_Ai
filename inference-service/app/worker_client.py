"""Facade → model worker (D24). MODEL_WORKER_URL empty = worker in this process (default, unchanged behaviour);
set = HTTP to app.worker_app with its own Bearer MODEL_WORKER_KEY. Only bytes/vectors/text cross this line."""

import base64
import json
import urllib.error
import urllib.request

from . import worker
from .config import settings
from .registry import registry

DEV_KEY = "sk-local-dev-key"
_TIMEOUT_S = 300  # ponytail: one budget for every op; long CPU summaries are the slowest. Per-op timeouts if a GPU worker needs tighter ones.


class DependencyError(RuntimeError):
    """Milvus/MinIO/remote worker behind a capability failed — reported in /health.dependencies, not as model failure."""

    def __init__(self, dependency: str, error: Exception):
        super().__init__(f"{type(error).__name__}: {error}")
        self.dependency = dependency


def remote() -> bool:
    return bool(settings.model_worker_url)


def is_real(name: str) -> bool:
    return name in registry.loaded if remote() else registry.is_real(name)


def _wire(value):
    if isinstance(value, bytes):
        return base64.b64encode(value).decode()
    if isinstance(value, list) and value and isinstance(value[0], bytes):
        return [base64.b64encode(v).decode() for v in value]
    return value


def _request(path: str, body: dict | None = None, timeout: float = _TIMEOUT_S):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(settings.model_worker_url + path, data=data, headers={
        "Authorization": f"Bearer {settings.model_worker_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — configured worker URL only
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())["error"]
        except Exception:  # noqa: BLE001 — tunnel/proxy pages are not JSON
            err = {"code": "HTTP_ERROR", "message": f"HTTP {e.code}"}
        if err["code"] == "VALIDATION_ERROR":
            raise worker.InvalidInput(err["message"]) from e
        if err["code"] == "MODEL_ERROR":
            raise RuntimeError(f"model worker: {err['message']}") from e
        raise DependencyError("model_worker", RuntimeError(f"HTTP {e.code} {err['code']}: {err['message']}")) from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise DependencyError("model_worker", e) from e
    registry.dependencies["model_worker"] = "ok"
    return out


def call(op: str, **kwargs):
    if not remote():
        return worker.OPS[op](**kwargs)
    return _request(f"/ops/{op}", {k: _wire(v) for k, v in kwargs.items()})["result"]


def attach() -> None:
    """Remote mode startup: refuse weak keys, then mirror the worker's models into the registry for /health."""
    key = settings.model_worker_key
    if len(key) < 24 or key in (DEV_KEY, settings.ai_service_key):
        raise RuntimeError("MODEL_WORKER_KEY must be a random key (≥24 chars), not sk-local-dev-key nor AI_SERVICE_KEY")
    info = _request("/info", timeout=30)
    registry.loaded[:] = info["models_loaded"]
    registry.stub_mode, registry.load_error, registry.device = info["stub_mode"], info["load_error"], info["device"]


def gpu_stats() -> tuple[float, float]:
    if not remote():
        return registry.gpu_stats()
    try:
        info = _request("/info", timeout=5)
    except Exception as e:  # noqa: BLE001 — /health must answer even when the worker is gone
        print(f"[worker_client] /info lỗi ({type(e).__name__}: {e})")
        registry.dependencies["model_worker"] = "unavailable"
        return 0.0, 0.0
    return info["gpu_vram_used"], info["gpu_util"]
