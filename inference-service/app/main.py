"""FastAPI inference-service — 1 process, 6 endpoint + /health, port 8001 (master plan §2.4)."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import schemas, services
from .auth import require_bearer
from .config import settings
from .gpu_queue import gpu_queue
from .registry import registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.load_all()
    gpu_queue.start()
    yield
    await gpu_queue.stop()


app = FastAPI(title="AI Inference Service", version="0.1.0", lifespan=lifespan)


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
    return await gpu_queue.submit(lambda: services.run_completion(req))


@app.post("/v1/asr/completions", response_model=schemas.ASRResponse, dependencies=[Depends(require_bearer)])
async def asr(req: schemas.ASRRequest):
    return await gpu_queue.submit(lambda: services.run_asr(req))


@app.post("/v1/highlight/completions", response_model=schemas.HighlightResponse, dependencies=[Depends(require_bearer)])
async def highlight(req: schemas.HighlightRequest):
    return await gpu_queue.submit(lambda: services.run_highlight(req))


@app.post("/v1/vision/completions", response_model=schemas.VisionResponse, dependencies=[Depends(require_bearer)])
async def vision(req: schemas.VisionRequest):
    return await gpu_queue.submit(lambda: services.run_vision(req))


# ---- nhẹ (encode + Milvus) — không chiếm GPU lâu ----

@app.post("/v1/search/completions", response_model=schemas.SearchResponse, dependencies=[Depends(require_bearer)])
async def search(req: schemas.SearchRequest):
    return services.run_search(req)


@app.post("/v1/recommendation/completions", response_model=schemas.RecommendationResponse,
          dependencies=[Depends(require_bearer)])
async def recommendation(req: schemas.RecommendationRequest):
    return services.run_recommendation(req)


# ---- health (proxy bởi gateway /api/cms/system/health) ----

@app.get("/health", response_model=schemas.HealthResponse)
async def health():
    vram, util = registry.gpu_stats()
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
        queue_depth=gpu_queue.depth,
        device=registry.device,
        stub_mode=registry.stub_mode,
        load_error=registry.load_error,
    )
