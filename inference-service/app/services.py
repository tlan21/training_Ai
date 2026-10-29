"""Facade logic 6 endpoint (D24): validation, error codes, MinIO/Milvus/audio I/O. Model inference goes through
worker_client (in-process worker.py by default, remote worker when MODEL_WORKER_URL is set); STUB đúng schema khi chưa có model.

GPU-bound (vision/asr/highlight/completions) chạy qua gpu_queue tuần tự.
search/recommendation: encode nhẹ + (thật) query Milvus — stub trả mock ổn định.
"""

import binascii
import hashlib
import io
import time
import uuid

from . import schemas, worker_client
from .registry import registry
from .config import settings
from .worker import InvalidInput
from .worker_client import DependencyError
from fastapi import HTTPException


def _warn(where: str, model_name: str, e: Exception) -> None:
    """Log lỗi real path; chỉ lỗi inference thật mới đánh dấu model degraded (D15). Status code giữ 503 như contract."""
    action = "fallback stub" if settings.force_stub else "request failed"
    print(f"[services] real path '{where}' (model {model_name}) lỗi ({type(e).__name__}: {e}) → {action}")
    if isinstance(e, DependencyError):
        registry.dependencies[e.dependency] = "unavailable"
    elif not isinstance(e, InvalidInput):
        registry.mark_degraded(model_name)
    if not settings.force_stub:
        raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "message": f"{where}: {type(e).__name__}: {e}"}) from e


def _now() -> int:
    return int(time.time())


def _rid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _seed_from(text: str) -> int:
    return int(hashlib.sha1(text.encode()).hexdigest(), 16) % (2 ** 31)


# ---------------- Summarizer /v1/completions ----------------

def run_completion(req: schemas.CompletionRequest) -> schemas.CompletionResponse:
    text = None
    if worker_client.is_real("minigpt"):
        try:
            text = _real_summarize(req)
            registry.degraded.discard("minigpt")
        except Exception as e:  # noqa: BLE001 — không bao giờ 500, fallback stub
            _warn("summarize", "minigpt", e)
    if text is None:
        # stub: cắt gọn prompt làm "tóm tắt" giả, độ dài theo max_tokens
        words = req.prompt.replace("\n", " ").split()
        text = " ".join(words[: max(1, req.max_tokens // 5)]) or "Tóm tắt (stub)."
    ptoks = len(req.prompt.split())
    ctoks = len(text.split())
    return schemas.CompletionResponse(
        id=_rid("cmpl-primitive"), created=_now(), model=req.model,
        choices=[schemas.CompletionChoice(text=text)],
        usage=schemas.Usage(prompt_tokens=ptoks, completion_tokens=ctoks, total_tokens=ptoks + ctoks),
    )


def _real_summarize(req: schemas.CompletionRequest) -> str:
    return worker_client.call("summarize", prompt=req.prompt, max_tokens=req.max_tokens, temperature=req.temperature)


# ---------------- Visual Search /v1/search/completions ----------------

def run_search(req: schemas.SearchRequest) -> schemas.SearchResponse:
    if not settings.force_stub:
        from . import visual_index
        t0 = time.perf_counter()
        bad_image = HTTPException(422, detail={"code": "VALIDATION_ERROR", "message": "Invalid JPEG/PNG/WebP image (max 20 megapixels)"})
        try:
            image = visual_index._image_bytes(req.image)
        except (OSError, ValueError, binascii.Error) as exc:
            raise bad_image from exc
        try:
            vector = visual_index.encode([image])[0]
        except InvalidInput as exc:
            raise bad_image from exc
        except Exception as exc:
            _warn("search/siamese", "siamese", exc)
        registry.degraded.discard("siamese")
        try:
            hits = visual_index.search(vector, req.top_k, req.threshold)
        except Exception as exc:
            _warn("search/milvus", "siamese", DependencyError("visual_index", exc))
        registry.dependencies["visual_index"] = "ok"
        return schemas.SearchResponse(
            id=_rid("vsearch-primitive"), created=_now(), model=req.model,
            results=[schemas.SearchResult(**hit) for hit in hits],
            query_metadata={"execution_time_ms": round((time.perf_counter() - t0) * 1000, 2)},
        )
    t0 = time.time()
    # stub: sinh kết quả ổn định theo ảnh, giảm dần similarity, lọc theo threshold
    rng = _seed_from(req.image[:64])
    results = []
    for i in range(req.top_k):
        sim = round(0.95 - i * 0.07, 3)
        if sim < req.threshold:
            break
        results.append(schemas.SearchResult(
            video_id=f"vid_{(rng + i) % 1000:03d}",
            timestamp=round((rng % 300) + i * 1.5, 1),
            similarity_score=sim,
            thumbnail_url=f"https://storage.local/thumbnails/vid_{(rng + i) % 1000:03d}.jpg",
        ))
    return schemas.SearchResponse(
        id=_rid("vsearch-primitive"), created=_now(), model=req.model, results=results,
        query_metadata={"execution_time_ms": int((time.time() - t0) * 1000),
                        "total_candidates_searched": 0 if registry.stub_mode else 15000},
    )


# ---------------- Highlight /v1/highlight/completions ----------------

def run_highlight(req: schemas.HighlightRequest) -> schemas.HighlightResponse:
    n = len(req.features.vision_embeddings)
    out = None
    if worker_client.is_real("highlight_fusion"):
        try:
            out = _real_highlight(req)
            registry.degraded.discard("highlight_fusion")
        except Exception as e:  # noqa: BLE001
            _warn("highlight", "highlight_fusion", e)
    if out is None:
        # stub: điểm dao động mượt theo index, thang 0–100
        scores = [round(50 + 40 * ((i * 37) % 100 - 50) / 50, 1) for i in range(n)]
        out = {"scores": [max(0.0, min(100.0, s)) for s in scores],
               "clip_rules": {"threshold": 75.0, "merge_gap_seconds": 0, "min_clip_seconds": 1, "min_video_seconds": 0}}
    scores, rules = out["scores"], out["clip_rules"]

    timeline = [schemas.TimelineScore(second=i, score=s) for i, s in enumerate(scores)]
    # Videos shorter than the recipe's minimum are outside the training distribution (~45 min halves): scores only, no clips.
    clips = [] if len(scores) < rules.get("min_video_seconds", 0) else _peaks_to_clips(
        scores, rules["threshold"], rules["merge_gap_seconds"], rules["min_clip_seconds"], req.asr_segments)
    return schemas.HighlightResponse(
        id=_rid("hl-primitive"), created=_now(), model=req.model, video_id=req.video_id,
        timeline_scores=timeline, recommended_clips=clips, clip_threshold=rules["threshold"],
    )


def _real_highlight(req: schemas.HighlightRequest) -> dict:
    return worker_client.call("highlight", vision=req.features.vision_embeddings, audio=req.features.audio_spectrogram_features)


_SNAP_SECONDS = 3.0  # ponytail: fixed reach; make it a recipe field if editors want tighter/looser cuts


def _peaks_to_clips(scores: list[float], threshold: float, merge_gap: int = 0, min_len: int = 1,
                    speech=None) -> list[schemas.RecommendedClip]:
    """Seconds with score > threshold → runs; runs ≤ merge_gap s apart join (AI-16 C); runs < min_len s drop.
    With ASR speech spans, a boundary inside a sentence moves to that sentence's edge if ≤ _SNAP_SECONDS away."""
    runs, start = [], None
    for i, s in enumerate(scores + [float("-inf")]):
        if s > threshold and start is None:
            start = i
        elif s <= threshold and start is not None:
            if runs and start - runs[-1][1] <= merge_gap:
                runs[-1][1] = i
            else:
                runs.append([start, i])
            start = None
    clips = []
    for a, b in runs:
        if b - a < min_len:
            continue
        begin, end = float(a), float(b)
        for span in speech or []:
            if span.start_time < begin < span.end_time and begin - span.start_time <= _SNAP_SECONDS:
                begin = span.start_time
            if span.start_time < end < span.end_time and span.end_time - end <= _SNAP_SECONDS:
                end = span.end_time
        seg = scores[a:b]
        clips.append(schemas.RecommendedClip(clip_id=f"clp_{a:04d}", start_time=max(0.0, begin), end_time=min(end, float(len(scores))),
                                             average_score=round(sum(seg) / len(seg), 1)))
    return clips


# ---------------- ASR /v1/asr/completions ----------------

def run_asr(req: schemas.ASRRequest) -> schemas.ASRResponse:
    result = None
    if worker_client.is_real("asr_ctc"):
        try:
            result = _real_asr(req)
            registry.degraded.discard("asr_ctc")
        except Exception as e:  # noqa: BLE001
            _warn("asr", "asr_ctc", e)
    if result is None:
        transcript = "Đây là bản phụ đề giả lập từ inference-service stub."
        segments = [
            schemas.ASRSegment(id=0, start_time=0.0, end_time=3.5,
                               text="Đây là bản phụ đề giả lập", confidence=0.9),
            schemas.ASRSegment(id=1, start_time=3.6, end_time=6.0,
                               text="từ inference-service stub.", confidence=0.88),
        ]
    else:
        transcript, segments = result
    return schemas.ASRResponse(
        id=_rid("asr-primitive"), created=_now(), model=req.model,
        full_transcript=transcript, segments=segments,
    )


def _fetch_audio(audio_url: str):
    """Tải audio (http(s) hoặc path cục bộ) → tensor 1D mono 16kHz. soundfile lazy."""
    import numpy as np
    import soundfile as sf
    import torch
    if audio_url.startswith(("http://", "https://")):
        import urllib.request
        with urllib.request.urlopen(audio_url) as r:  # noqa: S310 — nội bộ MinIO
            data, sr = sf.read(io.BytesIO(r.read()))
    else:
        data, sr = sf.read(audio_url)
    if getattr(data, "ndim", 1) > 1:
        data = data.mean(axis=1)
    if sr != 16000:
        n = int(len(data) * 16000 / sr)
        data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data)
    return torch.from_numpy(np.asarray(data)).float()


def _real_asr(req: schemas.ASRRequest):
    return _transcribe(_audio_chunks(req.audio_url))


def _transcribe(chunks):
    texts, segments = [], []
    offset = 0.0
    # Bound attention to 20 seconds; preserve absolute timestamps across windows.
    for chunk in chunks:
        duration = chunk.numel() / 16000
        if chunk.numel() < 400 or float(chunk.abs().max()) < 1e-4:
            offset += duration
            continue
        text, parts = _decode_asr(chunk)
        texts.append(text)
        for part in parts:
            part.id = len(segments)
            part.start_time += offset
            part.end_time += offset
            segments.append(part)
        offset += duration
    return " ".join(texts).strip(), segments


def _audio_chunks(audio_url):
    import soundfile as sf
    if audio_url.startswith(("http://", "https://")):
        # shortcut: direct HTTP audio loads whole; upload ingest uses streaming shared WAV paths.
        try:
            signal = _fetch_audio(audio_url)
        except Exception as e:
            raise InvalidInput(f"audio_url không đọc được: {type(e).__name__}: {e}") from e
        for start in range(0, signal.numel(), 20*16000):
            yield signal[start:start+20*16000]
        return
    try:
        audio = sf.SoundFile(audio_url)
    except Exception as e:
        raise InvalidInput(f"audio_url không đọc được: {type(e).__name__}: {e}") from e
    yield from _read_chunks(audio)


def _read_chunks(audio):
    """Open soundfile.SoundFile → 20 s float32 mono 16 kHz tensors (streamed, never the whole file)."""
    import numpy as np
    import torch
    with audio:
        while True:
            data = audio.read(20*audio.samplerate, dtype="float32")
            if not len(data):
                break
            if data.ndim > 1:
                data = data.mean(axis=1)
            if audio.samplerate != 16000:
                count = int(len(data)*16000/audio.samplerate)
                data = np.interp(np.linspace(0, len(data)-1, count), np.arange(len(data)), data)
            yield torch.from_numpy(np.asarray(data, dtype=np.float32))


def _decode_asr(signal):
    """One ≤20 s float32 16 kHz chunk → worker CTC → (text, segments with chunk-relative times)."""
    text, parts = worker_client.call("asr", pcm=signal.numpy().tobytes())
    return text, [schemas.ASRSegment(id=i, start_time=p["start"], end_time=p["end"], text=p["text"], confidence=p["confidence"])
                  for i, p in enumerate(parts)]


# ---------------- Recommendation /v1/recommendation/completions ----------------

_milvus_cache: dict = {}

# nprobe phải đủ lớn so với nlist của index (database_schema §4 đặt nlist=1024). Đo trên dữ liệu
# thật: nprobe=16 → 0 kết quả, nprobe≥64 → đúng top-10. Lấy 128 cho có biên; với collection nhỏ
# chi phí gần như không đổi (2.624 vector, 13 ms).
_NPROBE = 128


# ponytail: a failed dependency is re-probed at most every 30 s (requests + /health share the limit).
_DEP_RETRY_S = 30
_dep_checked: dict[str, float] = {}


def _due(name: str) -> bool:
    now = time.monotonic()
    if now - _dep_checked.get(name, float("-inf")) < _DEP_RETRY_S:
        return False
    _dep_checked[name] = now
    return True


def _milvus_collection():
    """Collection Two-Tower đã nối, hoặc None. Thất bại không cache vĩnh viễn: thử lại sau _DEP_RETRY_S."""
    if _milvus_cache.get("col") is not None:
        return _milvus_cache["col"]
    if not _due("recommendation_index"):
        return None
    from .config import settings

    try:
        from pymilvus import Collection, connections, utility

        connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port, timeout=3)
        if not utility.has_collection(settings.milvus_collection):
            print(f"[services] Milvus chưa có collection {settings.milvus_collection}")
            registry.dependencies["recommendation_index"] = "missing_collection"
            return None
        col = Collection(settings.milvus_collection)
        col.load()
    except Exception as e:
        print(f"[services] không nối được Milvus ({type(e).__name__}: {e}) → recommendation unavailable")
        registry.dependencies["recommendation_index"] = "unavailable"
        return None
    registry.dependencies["recommendation_index"] = "ok"
    _milvus_cache["col"] = col
    return col


def refresh_dependencies() -> None:
    """/health tự phục hồi: thử lại dependency chưa ok (giới hạn bởi _DEP_RETRY_S)."""
    if settings.force_stub:
        return
    if registry.dependencies.get("recommendation_index") != "ok":
        _milvus_collection()
    if registry.dependencies.get("visual_index") == "unavailable" and _due("visual_index"):
        from . import visual_index
        try:
            visual_index.search([1.0] * 128, 1, 2.0, timeout=2)   # threshold > 1: probe only, no hits returned
            registry.dependencies["visual_index"] = "ok"
        except Exception as e:  # noqa: BLE001
            print(f"[services] visual_index vẫn lỗi ({type(e).__name__}: {e})")


def _reco_from_milvus(user_id: str, limit: int) -> list[schemas.Recommendation] | None:
    """Vector user → ANN top-k video (IP). None = không dùng được, caller rơi về stub."""
    col = _milvus_collection()
    if col is None:
        return None
    got = col.query(expr=f'id == "{user_id}"', output_fields=["vector"], limit=1)
    if not got:
        # User chưa có vector (user mới, hoặc chưa export) — cold start, không phải lỗi.
        return None
    hits = col.search(
        data=[got[0]["vector"]], anns_field="vector",
        param={"metric_type": "IP", "params": {"nprobe": _NPROBE}},
        limit=limit, expr='type == "video"', output_fields=["id"],
    )[0]
    if not hits:
        # Đã cắn thật: index IVF_FLAT nlist=1024 trên 2.624 vector nên hầu hết cụm rỗng; kèm filter
        # `type == "video"` thì nprobe=16 dò trúng toàn cụm không có video → trả 0 hit, HTTP vẫn
        # 200 và client nhận danh sách RỖNG, không có lỗi nào. Rơi về stub và kêu to thay vì im.
        print(f"[services] Milvus trả 0 video cho {user_id} (nprobe={_NPROBE}) — "
              f"kiểm tra nlist/nprobe của {_milvus_cache.get('col')}")
        return None
    return [
        schemas.Recommendation(
            video_id=h.entity.get("id"),
            # IP trên vector đã L2-norm = cosine ∈ [-1,1]; schema quy ước 0–1 nên ánh xạ tuyến tính.
            score=round((float(h.score) + 1) / 2, 4),
        )
        for h in hits
    ]


def run_recommendation(req: schemas.RecommendationRequest) -> schemas.RecommendationResponse:
    recs = None
    try:
        recs = _reco_from_milvus(req.user_id, req.limit)
    except Exception as e:
        _milvus_cache.pop("col", None)       # reconnect on a later request instead of reusing a dead handle
        _warn("recommendation/milvus", "two_tower", DependencyError("recommendation_index", e))

    if recs is None:
        if not settings.force_stub:
            raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "message": "Recommendation index unavailable; gateway uses popularity fallback"})
        rng = _seed_from(req.user_id)
        recs = [
            schemas.Recommendation(video_id=f"vid_{(rng + i * 7) % 1000:03d}", score=round(0.99 - i * 0.03, 3))
            for i in range(req.limit)
        ]
        mode = "stub"
    else:
        mode = "personalized"
    return schemas.RecommendationResponse(
        id=_rid("rec-primitive"), created=_now(), model=req.model, recommendation_mode=mode, recommendations=recs,
    )


# ---------------- Vision /v1/vision/completions (nội bộ) ----------------

def run_vision(req: schemas.VisionRequest) -> schemas.VisionResponse:
    n = len(req.keyframes)
    result = None
    if worker_client.is_real("vit"):
        try:
            result = _real_vision(req)
        except Exception as e:  # noqa: BLE001
            _warn("vision", "vit", e)
    if result is None:
        category = "the_thao"
        embeddings = [[round(((i * 13 + j) % 100) / 100 - 0.5, 4) for j in range(256)] for i in range(n)]
    else:
        category, embeddings = result
    return schemas.VisionResponse(
        id=_rid("vis-primitive"), created=_now(), model=req.model,
        category_suggestion=category, embeddings_256=embeddings,
    )


def _real_vision(req: schemas.VisionRequest):
    from . import visual_index
    try:
        images = [visual_index._image_bytes(ref) for ref in req.keyframes]
    except (OSError, ValueError, binascii.Error) as e:
        raise InvalidInput(f"keyframe không đọc được (JPEG/PNG/WebP ≤20 MP): {type(e).__name__}: {e}") from e
    category, embeddings, _ = worker_client.call("vision", images=images)
    registry.degraded.discard("vit")
    if not settings.force_stub:
        try:
            indexed = visual_index.index_frames(req.keyframes, video_id=req.video_id)
        except DependencyError:
            raise
        except ValueError as e:
            raise InvalidInput(str(e)) from e
        except Exception as e:  # noqa: BLE001 — MinIO/Milvus behind the frame index
            raise DependencyError("visual_index", e) from e
        if indexed:
            registry.dependencies["visual_index"] = "ok"
    return category, embeddings
