import importlib.util
import json
from pathlib import Path

import pytest
import torch
from fastapi import HTTPException

from app import services, schemas


def test_real_failure_cannot_return_stub(monkeypatch):
    monkeypatch.setattr(services.settings, "force_stub", False)
    monkeypatch.setattr(services.registry, "models", {"vit": object()})
    with pytest.raises(HTTPException) as failure:
        services.run_vision(schemas.VisionRequest(keyframes=["not-a-real-image"]))
    assert failure.value.status_code == 503
    assert failure.value.detail["code"] == "AI_UNAVAILABLE"


def test_asr_windows_preserve_absolute_timestamps(monkeypatch):
    monkeypatch.setattr(services, "_audio_chunks", lambda _: (torch.ones(n*16000) for n in [20,20,5]))
    lengths = []
    def decode(signal):
        lengths.append(signal.numel())
        return "xin chào", [schemas.ASRSegment(id=0, start_time=1, end_time=2, text="xin chào")]
    monkeypatch.setattr(services, "_decode_asr", decode)
    text, parts = services._real_asr(schemas.ASRRequest(audio_url="a.wav"))
    assert lengths == [20*16000, 20*16000, 5*16000]
    assert [part.start_time for part in parts] == [1, 21, 41]
    assert [part.id for part in parts] == [0, 1, 2]
    assert text == "xin chào xin chào xin chào"


def test_highlight_is_bounded_and_zero_based(monkeypatch):
    lengths = []
    class Model:
        def __call__(self, vision, audio):
            assert vision.shape[1] == audio.shape[1]
            lengths.append(vision.shape[1])
            return torch.full((1, vision.shape[1]), 0.8)
    monkeypatch.setattr(services.registry, "models", {"highlight_fusion": Model()})
    request = schemas.HighlightRequest(video_id="vid_test", features=schemas.HighlightFeatures(
        vision_embeddings=[[0.0]*256]*241, audio_spectrogram_features=[[0.0]*64]*241))
    result = services.run_highlight(request)
    assert lengths == [120, 120, 1]
    assert [score.second for score in result.timeline_scores] == list(range(241))
    assert all(score.score == 80 for score in result.timeline_scores)


def test_highlight_threshold_is_strict():
    clips = services._peaks_to_clips([75.0, 75.1, 75.0], threshold=75.0)
    assert [(clip.start_time, clip.end_time) for clip in clips] == [(1.0, 2.0)]


def test_ingest_aligns_actual_frames_and_audio(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "ai-core"))
    script = root / "backend/ingest-worker/main.py"
    spec = importlib.util.spec_from_file_location("ingest", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    duration = module.preprocess(root / "e2e/fixtures/video.mp4", tmp_path)
    features = json.loads((tmp_path / "audio_features.json").read_text())
    assert duration == 8
    assert len(list(tmp_path.glob("*.jpg"))) == len(features) == 8
    assert all(len(row) == 64 for row in features)
    assert (tmp_path / "audio.wav").stat().st_size > 16000
