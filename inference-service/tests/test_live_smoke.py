"""Opt-in smoke against a RUNNING inference-service with real checkpoints (release gate, AI-01).

    INFERENCE_LIVE_URL=http://127.0.0.1:8001 INFERENCE_LIVE_KEY=<AI_SERVICE_KEY> pytest tests/test_live_smoke.py
Optional: INFERENCE_LIVE_MEDIA=<dir with *.jpg + clip.wav> (real media, else synthetic);
          INFERENCE_EXAMPLES_DIR=<dir> writes <endpoint>.{request,response,error}.json from these exact calls.
The server reads the WAV by path, so client and server must share the filesystem.
"""
import base64
import io
import json
import math
import os
import struct
import urllib.error
import urllib.request
import wave
from pathlib import Path

import pytest

from app import schemas

URL = os.environ.get("INFERENCE_LIVE_URL")
KEY = os.environ.get("INFERENCE_LIVE_KEY", "")
MEDIA = os.environ.get("INFERENCE_LIVE_MEDIA")
EXAMPLES = os.environ.get("INFERENCE_EXAMPLES_DIR")
MODELS = {"vit", "siamese", "asr_ctc", "highlight_fusion", "minigpt", "two_tower"}

pytestmark = pytest.mark.skipif(not URL, reason="set INFERENCE_LIVE_URL to smoke a running real service")


def _call(method, path, body=None, auth=True):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {KEY}"
    req = urllib.request.Request(URL + path, method=method, headers=headers,
                                 data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _save(name, kind, data):
    if EXAMPLES:
        Path(EXAMPLES).mkdir(parents=True, exist_ok=True)
        Path(EXAMPLES, f"{name}.{kind}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _example(name, method, path, body=None, auth=True, kind="response"):
    """Call once; with INFERENCE_EXAMPLES_DIR save the exact request and {http_status, body}."""
    if body is not None:
        _save(name, "request" if kind == "response" else "error_request", body)
    status, data = _call(method, path, body, auth)
    _save(name, kind, {"http_status": status, "body": data})
    return status, data


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    if MEDIA:
        frames = sorted(Path(MEDIA).glob("*.jpg"))[:3]
        return [f.read_bytes() for f in frames], str(Path(MEDIA, "clip.wav").resolve())
    from PIL import Image
    frames = []
    for i in range(3):
        buf = io.BytesIO()
        Image.new("RGB", (224, 224), (40 * i, 120, 200 - 40 * i)).save(buf, "JPEG")
        frames.append(buf.getvalue())
    wav = tmp_path_factory.mktemp("live") / "clip.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * t / 16000))) for t in range(3 * 16000)))
    return frames, str(wav)


def _data_uri(jpg):
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode()


def test_health_real_and_auth():
    status, body = _example("health", "GET", "/health", auth=False)
    health = schemas.HealthResponse.model_validate(body)
    assert status == 200 and not health.stub_mode and set(health.models_loaded) == MODELS
    status, body = _example("completions", "POST", "/v1/completions", {"prompt": "x", "max_tokens": 1}, auth=False, kind="error")
    assert status == 401 and body["error"]["code"] == "UNAUTHORIZED"


def test_vision_then_highlight(media):
    frames, wav = media
    status, body = _example("vision", "POST", "/v1/vision/completions", {"keyframes": [_data_uri(f) for f in frames]})
    vision = schemas.VisionResponse.model_validate(body)
    assert status == 200 and vision.category_suggestion in {"bong_da", "the_thao", "ca_nhac", "tin_tuc"}
    assert len(vision.embeddings_256) == len(frames) and all(len(e) == 256 for e in vision.embeddings_256)
    status, body = _example("vision", "POST", "/v1/vision/completions", {}, kind="error")
    assert status == 422 and body["error"]["code"] == "VALIDATION_ERROR"

    import soundfile as sf
    import torch
    from ai_core.audio.features import audio_features_per_second
    signal, sr = sf.read(wav, dtype="float32")
    audio = audio_features_per_second(torch.from_numpy(signal), sr).tolist()
    n = min(len(audio), len(frames))
    req = {"video_id": "vid_ai01example", "features": {"vision_embeddings": vision.embeddings_256[:n], "audio_spectrogram_features": audio[:n]}}
    status, body = _example("highlight", "POST", "/v1/highlight/completions", req)
    hl = schemas.HighlightResponse.model_validate(body)
    assert status == 200 and [s.second for s in hl.timeline_scores] == list(range(n))
    assert all(0 <= s.score <= 100 for s in hl.timeline_scores)
    bad = {"video_id": "vid_ai01example", "features": {"vision_embeddings": vision.embeddings_256[:n], "audio_spectrogram_features": audio[: n - 1]}}
    status, body = _example("highlight", "POST", "/v1/highlight/completions", bad, kind="error")
    assert status == 503 and body["error"]["code"] == "AI_UNAVAILABLE"
    assert "highlight_fusion" not in _call("GET", "/health", auth=False)[1]["degraded"]   # bad input ≠ model failure


def test_asr(media):
    _, wav = media
    status, body = _example("asr", "POST", "/v1/asr/completions", {"audio_url": wav, "language": "vi"})
    asr = schemas.ASRResponse.model_validate(body)
    assert status == 200 and all(0 <= s.start_time <= s.end_time for s in asr.segments)
    status, body = _example("asr", "POST", "/v1/asr/completions", {"audio_url": wav + ".missing.wav", "language": "vi"}, kind="error")
    assert status == 503 and body["error"]["code"] == "AI_UNAVAILABLE"
    assert "asr_ctc" not in _call("GET", "/health", auth=False)[1]["degraded"]   # bad input ≠ model failure


def test_completions():
    prompt = ("Tóm tắt: Chiều nay tại Hà Nội, đội tuyển bóng đá quốc gia đã có buổi tập đầu tiên chuẩn bị cho vòng loại. "
              "Huấn luyện viên cho biết toàn đội đang trong trạng thái tốt và quyết tâm giành chiến thắng.")
    status, body = _example("completions", "POST", "/v1/completions", {"prompt": prompt, "max_tokens": 48, "temperature": 0})
    out = schemas.CompletionResponse.model_validate(body)
    assert status == 200 and out.choices[0].text.strip() and out.usage.completion_tokens <= 48


def test_search_needs_milvus(media):
    frames, _ = media
    status, body = _example("search", "POST", "/v1/search/completions", {"image": _data_uri(frames[0]), "top_k": 5, "threshold": 0.0})
    out = schemas.SearchResponse.model_validate(body)
    assert status == 200 and len(out.results) <= 5 and all(0 <= r.similarity_score <= 1 for r in out.results)
    status, body = _example("search", "POST", "/v1/search/completions", {"image": _data_uri(frames[0]), "top_k": 0}, kind="error")
    assert status == 422 and body["error"]["code"] == "VALIDATION_ERROR"
    assert _call("GET", "/health", auth=False)[1]["dependencies"]["visual_index"] == "ok"


def test_recommendation_contract():
    status, body = _example("recommendation", "POST", "/v1/recommendation/completions", {"user_id": "usr_ai01example", "limit": 5, "context": {}})
    if status == 200:
        schemas.RecommendationResponse.model_validate(body)
    else:  # index missing or user without vector: gateway falls back to popularity
        assert status == 503 and body["error"]["code"] == "AI_UNAVAILABLE"
    health = _call("GET", "/health", auth=False)[1]
    assert health["dependencies"]["recommendation_index"] in {"ok", "missing_collection", "unavailable"}
    assert "two_tower" not in health["degraded"]
