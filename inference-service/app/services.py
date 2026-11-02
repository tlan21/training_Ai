"""Facade logic (D24, AI-API v3.0): validation + error codes; model inference goes through worker_client (in-process
worker.py by default, remote worker when MODEL_WORKER_URL is set); STUB đúng schema khi chưa có model.
No MinIO/Milvus here (AI-23): the backend owns storage and vector search; /v2 (v2.py) returns vectors only.

GPU-bound (highlight/completions + /v2 vision/asr) chạy qua gpu_queue tuần tự.
"""

import hashlib
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


# ---------------- ASR helpers (shared with /v2/asr/completions) ----------------

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
