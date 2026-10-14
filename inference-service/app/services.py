"""Logic 6 endpoint. Model thật (registry) khi có checkpoint; STUB đúng schema khi chưa.

GPU-bound (vision/asr/highlight/completions) chạy qua gpu_queue tuần tự.
search/recommendation: encode nhẹ + (thật) query Milvus — stub trả mock ổn định.
"""

import base64
import binascii
import hashlib
import io
import time
import uuid

from . import schemas
from .registry import registry
from .config import settings
from fastapi import HTTPException


def _warn(where: str, model_name: str, e: Exception) -> None:
    """Log lỗi real path + đánh dấu model degraded (health phản ánh) — không âm thầm nuốt lỗi."""
    action = "fallback stub" if settings.force_stub else "request failed"
    print(f"[services] real path '{where}' (model {model_name}) lỗi ({type(e).__name__}: {e}) → {action}")
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
    if registry.is_real("minigpt"):
        try:
            text = _real_summarize(req)
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


_SUM_CHUNK = 900   # ~900 token/đoạn (dưới context 1024 Mini-GPT)


def _real_summarize(req: schemas.CompletionRequest) -> str:
    """Map-reduce cho transcript >1024 token (master plan §2.4 / architecture §2.1):
    chia đoạn ~900 token → tóm tắt từng đoạn → nối → tóm tắt lần cuối."""
    import torch
    model = registry.models["minigpt"]
    tok = registry.tokenizer
    if tok is None:
        raise RuntimeError("minigpt checkpoint thiếu BPE vocabulary")
    eos = tok.special_tokens.get("<eos>")

    def _gen(prompt_ids: list[int]) -> str:
        prompt_ids = prompt_ids[-_SUM_CHUNK:]
        out = model.generate(
            torch.tensor([prompt_ids], device=registry.device),
            max_new_tokens=req.max_tokens, temperature=req.temperature, eos_id=eos,
        )
        return tok.decode(out[0, len(prompt_ids):].tolist()).strip()

    ids = tok.encode(req.prompt, add_bos=True)
    if len(ids) <= _SUM_CHUNK:
        return _gen(ids)
    # map: tóm tắt từng đoạn ~900 token
    partials = [_gen(ids[i:i + _SUM_CHUNK]) for i in range(0, len(ids), _SUM_CHUNK)]
    # reduce: tóm tắt bản nối các tóm tắt đoạn
    return _gen(tok.encode(" ".join(partials), add_bos=True))


# ---------------- Visual Search /v1/search/completions ----------------

def run_search(req: schemas.SearchRequest) -> schemas.SearchResponse:
    if not settings.force_stub:
        from . import visual_index
        t0 = time.perf_counter()
        try:
            image = _load_keyframe(req.image)
        except (OSError, ValueError, binascii.Error) as exc:
            raise HTTPException(422, detail={"code": "VALIDATION_ERROR", "message": "Invalid JPEG/PNG/WebP image (max 20 megapixels)"}) from exc
        try:
            vector = visual_index.encode([image])[0]
            hits = visual_index.search(vector, req.top_k, req.threshold)
        except Exception as exc:
            _warn("search/siamese/milvus", "siamese", exc)
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
    scores = None
    if registry.is_real("highlight_fusion"):
        try:
            scores = _real_highlight(req)
        except Exception as e:  # noqa: BLE001
            _warn("highlight", "highlight_fusion", e)
    if scores is None:
        # stub: điểm dao động mượt theo index, thang 0–100
        scores = [round(50 + 40 * ((i * 37) % 100 - 50) / 50, 1) for i in range(n)]
        scores = [max(0.0, min(100.0, s)) for s in scores]

    timeline = [schemas.TimelineScore(second=i, score=s) for i, s in enumerate(scores)]
    clips = _peaks_to_clips(scores, threshold=75.0)
    return schemas.HighlightResponse(
        id=_rid("hl-primitive"), created=_now(), model=req.model, video_id=req.video_id,
        timeline_scores=timeline, recommended_clips=clips,
    )


def _real_highlight(req: schemas.HighlightRequest) -> list[float]:
    import torch
    model = registry.models["highlight_fusion"]
    dt = registry.model_dtype                     # khớp dtype model (half trên CUDA) để tránh mismatch
    if len(req.features.vision_embeddings) != len(req.features.audio_spectrogram_features):
        raise ValueError("vision_embeddings và audio_spectrogram_features phải cùng số giây")
    if not req.features.vision_embeddings:
        raise ValueError("empty highlight features")
    scores = []
    window = 120  # Same window length used to train the Fusion checkpoint.
    with torch.no_grad():
        for start in range(0, len(req.features.vision_embeddings), window):
            v = torch.tensor([req.features.vision_embeddings[start:start+window]], device=registry.device, dtype=dt)
            a = torch.tensor([req.features.audio_spectrogram_features[start:start+window]], device=registry.device, dtype=dt)
            scores.extend(round(float(x) * 100, 1) for x in model(v, a)[0])
    return scores


def _peaks_to_clips(scores: list[float], threshold: float) -> list[schemas.RecommendedClip]:
    clips, start = [], None
    for i, s in enumerate(scores):
        if s > threshold and start is None:
            start = i
        elif s <= threshold and start is not None:
            seg = scores[start:i]
            clips.append(schemas.RecommendedClip(
                clip_id=f"clp_{start:04d}", start_time=float(start), end_time=float(i),
                average_score=round(sum(seg) / len(seg), 1)))
            start = None
    if start is not None:
        seg = scores[start:]
        clips.append(schemas.RecommendedClip(
            clip_id=f"clp_{start:04d}", start_time=float(start), end_time=float(len(scores)),
            average_score=round(sum(seg) / len(seg), 1)))
    return clips


# ---------------- ASR /v1/asr/completions ----------------

def run_asr(req: schemas.ASRRequest) -> schemas.ASRResponse:
    result = None
    if registry.is_real("asr_ctc"):
        try:
            result = _real_asr(req)
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
    texts, segments = [], []
    offset = 0.0
    # Bound attention to 20 seconds; preserve absolute timestamps across windows.
    for chunk in _audio_chunks(req.audio_url):
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
    import numpy as np
    import soundfile as sf
    import torch
    if audio_url.startswith(("http://", "https://")):
        # shortcut: direct HTTP audio loads whole; upload ingest uses streaming shared WAV paths.
        signal = _fetch_audio(audio_url)
        for start in range(0, signal.numel(), 20*16000):
            yield signal[start:start+20*16000]
        return
    with sf.SoundFile(audio_url) as audio:
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
    import torch
    from ai_core.audio.mel import log_mel_spectrogram
    from ai_core.models.ctc import ctc_greedy_decode, ctc_segments
    vocab = registry.asr_vocab
    if vocab is None:
        raise NotImplementedError("thiếu char_vocab cho ASR (checkpoints/asr_ctc/vocab.json)")
    model = registry.models["asr_ctc"]
    mel = log_mel_spectrogram(signal, n_mels=80, sr=16000).unsqueeze(0).to(
        device=registry.device, dtype=registry.model_dtype)          # khớp dtype model
    lengths = torch.tensor([mel.shape[2]], device=registry.device)
    with torch.no_grad():
        log_probs, out_len = model(mel, lengths)         # (1, T', C)
    lp = log_probs.float().cpu()
    valid = int(out_len[0].item())                       # bỏ frame padding khi tính conf
    ids = ctc_greedy_decode(lp, out_len.cpu(), blank=0)[0]
    text = "".join(vocab[i] for i in ids if 0 < i < len(vocab))
    conf = float(lp[0, :valid].max(-1).values.exp().mean()) if valid > 0 else 0.0

    # Timestamp THẬT từ alignment CTC. Bản trước trả đúng một segment 0 → len(audio): khớp schema,
    # trông như chạy được, nhưng không dựng nổi phụ đề vì mọi dòng cùng một mốc thời gian.
    # frame_sec = hop/sr × subsample; suy subsample từ chính đầu ra model để encoder đổi tỉ lệ thì
    # timestamp không lệch âm thầm.
    subsample = mel.shape[2] / max(valid, 1)
    parts = ctc_segments(lp[0], valid, vocab, 160 / 16000 * subsample, blank=0)
    dur = round(signal.numel() / 16000, 2)
    if not parts:
        parts = [{"start": 0.0, "end": dur, "text": text}]
    segs = [
        schemas.ASRSegment(id=i, start_time=p["start"], end_time=min(p["end"], dur),
                           text=p["text"], confidence=round(conf, 3))
        for i, p in enumerate(parts)
    ]
    return text, segs


# ---------------- Recommendation /v1/recommendation/completions ----------------

_milvus_cache: dict = {}

# nprobe phải đủ lớn so với nlist của index (database_schema §4 đặt nlist=1024). Đo trên dữ liệu
# thật: nprobe=16 → 0 kết quả, nprobe≥64 → đúng top-10. Lấy 128 cho có biên; với collection nhỏ
# chi phí gần như không đổi (2.624 vector, 13 ms).
_NPROBE = 128


def _milvus_collection():
    """Collection Two-Tower, cache lại. None nếu không nối được → endpoint rơi về stub."""
    if "col" in _milvus_cache:
        return _milvus_cache["col"]
    from .config import settings

    col = None
    try:
        from pymilvus import Collection, connections, utility

        connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port, timeout=3)
        if utility.has_collection(settings.milvus_collection):
            col = Collection(settings.milvus_collection)
            col.load()
        else:
            print(f"[services] Milvus chưa có collection {settings.milvus_collection}")
    except Exception as e:
        print(f"[services] không nối được Milvus ({type(e).__name__}: {e}) → recommendation unavailable")
    _milvus_cache["col"] = col
    return col


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
            title=f"Video {h.entity.get('id')}",
            thumbnail_url=f"https://storage.local/thumbnails/{h.entity.get('id')}.jpg",
        )
        for h in hits
    ]


def run_recommendation(req: schemas.RecommendationRequest) -> schemas.RecommendationResponse:
    recs = None
    try:
        recs = _reco_from_milvus(req.user_id, req.limit)
    except Exception as e:
        _warn("recommendation/milvus", "two_tower", e)

    if recs is None:
        if not settings.force_stub:
            raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "message": "Recommendation index unavailable; gateway uses popularity fallback"})
        rng = _seed_from(req.user_id)
        recs = [
            schemas.Recommendation(
                video_id=f"vid_{(rng + i * 7) % 1000:03d}",
                score=round(0.99 - i * 0.03, 3),
                title=f"Video gợi ý #{i + 1}",
                thumbnail_url=f"https://storage.local/thumbnails/vid_{(rng + i * 7) % 1000:03d}.jpg",
            )
            for i in range(req.limit)
        ]
    return schemas.RecommendationResponse(
        id=_rid("rec-primitive"), created=_now(), model=req.model, recommendations=recs,
    )


# ---------------- Vision /v1/vision/completions (nội bộ) ----------------

def run_vision(req: schemas.VisionRequest) -> schemas.VisionResponse:
    n = len(req.keyframes)
    result = None
    if registry.is_real("vit"):
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


def _load_keyframe(ref: str, img_size: int = 224):
    """Keyframe từ data URI base64 hoặc path → tensor (3, H, W) [0,1]."""
    import os

    import numpy as np
    import torch
    from PIL import Image
    if ref.startswith("data:"):                      # data URI → phần base64 sau dấu phẩy
        img = Image.open(io.BytesIO(base64.b64decode(ref.split(",", 1)[1])))
    elif os.path.exists(ref):                        # path cục bộ
        img = Image.open(ref)
    else:                                            # base64 trần
        img = Image.open(io.BytesIO(base64.b64decode(ref)))
    if img.width * img.height > 20_000_000:
        raise ValueError("Image exceeds 20 megapixels")
    img = img.convert("RGB").resize((img_size, img_size))
    return torch.from_numpy(np.asarray(img)).float().div(255.0).permute(2, 0, 1)


def _real_vision(req: schemas.VisionRequest):
    import torch
    model = registry.models["vit"]
    if not req.keyframes:
        raise ValueError("empty keyframes")
    embeddings, total_logits = [], None
    with torch.no_grad():
        for start in range(0, len(req.keyframes), 16):
            imgs = torch.stack([_load_keyframe(k) for k in req.keyframes[start:start+16]]).to(device=registry.device, dtype=registry.model_dtype)
            logits, emb = model(imgs, return_embedding=True)
            summed = logits.float().sum(0)
            total_logits = summed if total_logits is None else total_logits + summed
            embeddings.extend(emb.float().cpu().tolist())
    idx = int(total_logits.argmax().item())
    classes = registry.vit_classes
    category = classes[idx] if classes and idx < len(classes) else f"class_{idx}"
    if not settings.force_stub:
        from .visual_index import index_frames
        index_frames(req.keyframes)
    return category, embeddings
