"""FastAPI inference-service — compute only (D24, AI-API v3.0): /v1/highlight, /v1/completions, /v2/*, /health; port 8001."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import schemas, services, v2, worker_client
from .auth import require_bearer
from .config import settings
from .gpu_queue import gpu_queue
from .registry import registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    if worker_client.remote() and not settings.force_stub:
        worker_client.attach()          # D24: models live in the remote worker; this process is the facade only
    else:
        registry.load_all()
    if not settings.force_stub and registry.stub_mode:
        raise RuntimeError(f"Real inference requires all checkpoints: {registry.load_error}")
    gpu_queue.start()
    yield
    await gpu_queue.stop()


app = FastAPI(title="AI Inference Service", version="0.1.0", lifespan=lifespan)
app.include_router(v2.router)   # D24 compute-only endpoints; AI-23 removed /v1 vision|asr|search|recommendation (MinIO/Milvus)


# ---- error envelope {"error":{"code","message"}} (master plan §2.6) ----

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"error": detail}
    else:
        body = {"error": {"code": "HTTP_ERROR", "message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422,
                        content={"error": {"code": "VALIDATION_ERROR", "message": str(exc.errors())}})


# ---- GPU-bound endpoints qua hàng đợi tuần tự ----

@app.post("/v1/completions", response_model=schemas.CompletionResponse, dependencies=[Depends(require_bearer)])
async def completions(req: schemas.CompletionRequest):
    return await gpu_queue.submit(lambda: services.run_completion(req), "summary")


@app.post("/v1/highlight/completions", response_model=schemas.HighlightResponse, dependencies=[Depends(require_bearer)])
async def highlight(req: schemas.HighlightRequest):
    return await gpu_queue.submit(lambda: services.run_highlight(req), "highlight")


# ---- health (proxy bởi gateway /api/cms/system/health) ----

@app.get("/health", response_model=schemas.HealthResponse)
async def health():
    vram, util = await asyncio.to_thread(worker_client.gpu_stats)
    all_names = ["vit", "siamese", "asr_ctc", "highlight_fusion", "minigpt", "two_tower"]
    return schemas.HealthResponse(
        status="ok",
        gpu_vram_used=round(vram, 1),
        gpu_util=util,
        # Báo ĐÚNG model đã nạp thật, không trả [] chỉ vì còn thiếu model khác. Bản cũ ẩn hết nếu
        # bất kỳ model nào vắng: giai đoạn train tuần tự lúc nào cũng thiếu vài model, nên /health
        # nói "không nạp gì" trong khi endpoint ASR đang chạy checkpoint thật. `stub_mode` vẫn cho
        # biết đã đủ 6 model hay chưa (điều kiện T1.8) nên không mất thông tin nào.
        models_loaded=sorted(registry.loaded),
        degraded=sorted(registry.degraded),
        dependencies=dict(sorted(registry.dependencies.items())),
        queue_depth=gpu_queue.depth,
        device=registry.device,
        stub_mode=registry.stub_mode,
        load_error=registry.load_error,
    )
