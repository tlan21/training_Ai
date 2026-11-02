"""AI-API v2 endpoints (D24, AI-15; API_READY): compute-only. Bytes/vectors/text in → labels/vectors/text out.

No MinIO, no Milvus, no server paths: the backend stores thumbnails/vectors and searches Milvus itself.
Bad input = 422 VALIDATION_ERROR (v1 answered 503 for unreadable media); model failure = 503 AI_UNAVAILABLE.
"""

import base64
import binascii
import io
import math
import random

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from . import schemas, services, worker_client
from .auth import require_bearer
from .config import settings
from .gpu_queue import gpu_queue
from .registry import registry
from .worker import InvalidInput

router = APIRouter(prefix="/v2", dependencies=[Depends(require_bearer)])
MAX_AUDIO_BYTES = 64 * 1024 * 1024   # ≈ 35 min of 16 kHz mono PCM16 WAV; longer audio → backend splits (contract §5)


def _invalid(message: str) -> HTTPException:
    return HTTPException(422, detail={"code": "VALIDATION_ERROR", "message": message})


def _image(ref: str) -> bytes:
    try:
        return base64.b64decode(ref.split(",", 1)[1] if ref.startswith("data:") else ref, validate=True)
    except (binascii.Error, ValueError, IndexError) as e:
        raise _invalid(f"image is not data URI/base64: {type(e).__name__}") from e


def _infer(model_name: str, where: str, fn):
    """Real inference; InvalidInput → 422, anything else → 503 + degraded/dependency status (D15)."""
    try:
        out = fn()
    except InvalidInput as e:
        raise _invalid(str(e)) from e
    except Exception as e:  # noqa: BLE001
        services._warn(where, model_name, e)
        raise
    registry.degraded.discard(model_name)
    return out


def _stub_vector(key: str) -> list[float]:
    rng = random.Random(services._seed_from(key))
    v = [rng.gauss(0, 1) for _ in range(128)]
    norm = math.sqrt(sum(x * x for x in v))
    return [round(x / norm, 6) for x in v]


def _real(name: str) -> bool:
    return not settings.force_stub and worker_client.is_real(name)


def run_vision(req: schemas.VisionV2Request) -> schemas.VisionV2Response:
    images = [_image(k) for k in req.keyframes]
    if _real("vit") and _real("siamese"):
        category, embeddings, sums = _infer("vit", "v2/vision", lambda: worker_client.call("vision", images=images))
        vectors = _infer("siamese", "v2/vision/siamese", lambda: [
            v for i in range(0, len(images), 16) for v in worker_client.call("siamese", images=images[i:i + 16])])
    else:
        category, sums = "the_thao", {"bong_da": 0.0, "the_thao": float(len(images)), "ca_nhac": 0.0, "tin_tuc": 0.0}
        embeddings = [[round(((i * 13 + j) % 100) / 100 - 0.5, 4) for j in range(256)] for i in range(len(images))]
        vectors = [_stub_vector(k[:64] + str(i)) for i, k in enumerate(req.keyframes)]
    return schemas.VisionV2Response(
        id=services._rid("vis-primitive"), created=services._now(), model=req.model, category_suggestion=category,
        category_logit_sums=sums, embeddings_256=embeddings, siamese_vectors=vectors)


def run_search_embedding(req: schemas.SearchEmbeddingRequest) -> schemas.SearchEmbeddingResponse:
    image = _image(req.image)
    if _real("siamese"):
        vector = _infer("siamese", "v2/search", lambda: worker_client.call("siamese", images=[image])[0])
    else:
        vector = _stub_vector(req.image[:64])
    return schemas.SearchEmbeddingResponse(id=services._rid("vsearch-primitive"), created=services._now(), model=req.model, vector=vector)


def run_asr(data: bytes, offset_seconds: float, model: str) -> schemas.ASRResponse:
    if _real("asr_ctc"):
        import soundfile as sf

        def transcribe():
            try:
                audio = sf.SoundFile(io.BytesIO(data))
            except Exception as e:  # noqa: BLE001 — libsndfile reports every unreadable format differently
                raise InvalidInput(f"audio không đọc được (WAV/FLAC/OGG): {type(e).__name__}: {e}") from e
            return services._transcribe(services._read_chunks(audio))
        transcript, segments = _infer("asr_ctc", "v2/asr", transcribe)
    else:
        transcript = "Đây là bản phụ đề giả lập từ inference-service stub."
        segments = [schemas.ASRSegment(id=0, start_time=0.0, end_time=3.5, text="Đây là bản phụ đề giả lập", confidence=0.9),
                    schemas.ASRSegment(id=1, start_time=3.6, end_time=6.0, text="từ inference-service stub.", confidence=0.88)]
    for s in segments:
        s.start_time = round(s.start_time + offset_seconds, 3)
        s.end_time = round(s.end_time + offset_seconds, 3)
    return schemas.ASRResponse(id=services._rid("asr-primitive"), created=services._now(), model=model,
                               full_transcript=transcript, segments=segments)


def run_reco_embeddings(req: schemas.RecoEmbeddingRequest) -> schemas.RecoEmbeddingResponse:
    known = {v.video_id for v in req.videos}
    for u in req.users:
        missing = [v for v in u.positive_video_ids if v not in known]
        if missing:
            raise _invalid(f"{u.user_id}: positive_video_ids not in videos: {missing[:5]}")
    if not settings.force_stub:
        # ponytail: the active two_tower is MovieLens v1 (cannot encode usr_/vid_). Add a worker op when AI-12 promotes a v2 checkpoint.
        raise HTTPException(503, detail={"code": "MODEL_NOT_READY",
                                         "message": "Two-Tower v2 checkpoint not trained yet (AI-12); gateway keeps popularity fallback"})
    return schemas.RecoEmbeddingResponse(
        id=services._rid("rec-primitive"), created=services._now(), model=req.model,
        videos=[schemas.VideoVector(video_id=v.video_id, vector=_stub_vector(v.video_id)) for v in req.videos],
        users=[schemas.UserVector(user_id=u.user_id, vector=_stub_vector(u.user_id)) for u in req.users])


@router.post("/vision/completions", response_model=schemas.VisionV2Response)
async def vision(req: schemas.VisionV2Request):
    return await gpu_queue.submit(lambda: run_vision(req), "v2/vision")


@router.post("/search/embeddings", response_model=schemas.SearchEmbeddingResponse)
def search_embedding(req: schemas.SearchEmbeddingRequest):
    return run_search_embedding(req)


@router.post("/asr/completions", response_model=schemas.ASRResponse)
async def asr(file: UploadFile = File(..., description="WAV/FLAC/OGG; khuyến nghị 16 kHz mono PCM16"),
              language: str = Form("vi"), model: str = Form("primitive-asr-transformer"),
              offset_seconds: float = Form(0.0, ge=0, description="cộng vào mọi timestamp khi backend chia file dài")):
    data = await file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, detail={"code": "PAYLOAD_TOO_LARGE", "message": f"audio > {MAX_AUDIO_BYTES} bytes; split it (contract §5)"})
    if language != "vi":
        raise _invalid("only language=vi is supported")
    return await gpu_queue.submit(lambda: run_asr(data, offset_seconds, model), "v2/asr")


@router.post("/recommendation/embeddings", response_model=schemas.RecoEmbeddingResponse)
def reco_embeddings(req: schemas.RecoEmbeddingRequest):
    return run_reco_embeddings(req)
