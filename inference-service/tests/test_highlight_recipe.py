"""AI-16: served highlight = the recipe the DoD was measured with; clip rules (merge gap, min length, sentence snap)."""
import random

import pytest
import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.eval_highlight import model_scores_overlap, smooth
from app import schemas, services, worker
from app.registry import registry


def tiny_fusion(seed):
    torch.manual_seed(seed)
    return build_model("highlight_fusion", ModelConfig(name="highlight_fusion", d_model=16, n_heads=2, dropout=0.0)).eval()


@pytest.fixture
def recipe(monkeypatch):
    members = [tiny_fusion(s) for s in (1, 2, 3)]
    rules = {"stride": 30, "smooth_k": 9, "tau": 0.51, "merge_gap_seconds": 2, "min_clip_seconds": 3}
    monkeypatch.setattr(registry, "models", {"highlight_fusion": members[0]})
    monkeypatch.setattr(registry, "highlight_members", members)
    monkeypatch.setattr(registry, "highlight_postproc", rules)
    monkeypatch.setattr(registry, "device", "cpu")
    return members, rules


@pytest.mark.parametrize("n", [50, 120, 301])          # shorter than, equal to, and longer than one window
def test_recipe_is_exactly_the_evaluated_dod_pipeline(recipe, n):
    members, rules = recipe
    torch.manual_seed(n)
    sample = {"vision": torch.randn(n, 256), "audio": torch.randn(n, 64)}
    with torch.no_grad():
        expected = smooth(torch.stack([model_scores_overlap(m, sample, 120, 30) for m in members]).mean(0), 9)
    out = worker.highlight(sample["vision"].tolist(), sample["audio"].tolist())
    assert out["scores"] == [round(float(x) * 100, 1) for x in expected]
    assert out["clip_rules"] == {"threshold": 51.0, "merge_gap_seconds": 2, "min_clip_seconds": 3, "min_video_seconds": 0}


def test_feature_norm_recipe_matches_pipeline_on_normalised_features(recipe):
    from ai_core.training.datasets.highlight_dataset import normalize_per_video
    members, rules = recipe
    rules["feature_norm"] = "per_video"
    torch.manual_seed(7)
    v, a = torch.randn(200, 256) * 4 + 2, torch.randn(200, 64) * 3
    with torch.no_grad():
        sample = {"vision": normalize_per_video(v), "audio": normalize_per_video(a)}
        expected = smooth(torch.stack([model_scores_overlap(m, sample, 120, 30) for m in members]).mean(0), 9)
    assert worker.highlight(v.tolist(), a.tolist())["scores"] == [round(float(x) * 100, 1) for x in expected]


def test_no_recipe_keeps_legacy_scoring(monkeypatch):
    model = tiny_fusion(1)
    monkeypatch.setattr(registry, "models", {"highlight_fusion": model})
    monkeypatch.setattr(registry, "highlight_members", [])
    monkeypatch.setattr(registry, "highlight_postproc", {})
    monkeypatch.setattr(registry, "device", "cpu")
    v, a = torch.randn(130, 256), torch.randn(130, 64)
    with torch.no_grad():
        legacy = [round(float(x) * 100, 1) for s in range(0, 130, 120) for x in model(v[None, s:s + 120], a[None, s:s + 120])[0]]
    out = worker.highlight(v.tolist(), a.tolist())
    assert out["scores"] == legacy and out["clip_rules"]["threshold"] == 75.0


def _old_peaks_to_clips(scores, threshold):            # pre-AI-16 implementation, kept here as the legacy oracle
    clips, start = [], None
    for i, s in enumerate(scores):
        if s > threshold and start is None:
            start = i
        elif s <= threshold and start is not None:
            clips.append((float(start), float(i), round(sum(scores[start:i]) / (i - start), 1)))
            start = None
    if start is not None:
        clips.append((float(start), float(len(scores)), round(sum(scores[start:]) / (len(scores) - start), 1)))
    return clips


def test_default_rules_reproduce_legacy_clips():
    rng = random.Random(0)
    for _ in range(50):
        scores = [round(rng.uniform(0, 100), 1) for _ in range(rng.randint(1, 200))]
        got = [(c.start_time, c.end_time, c.average_score) for c in services._peaks_to_clips(scores, 75.0)]
        assert got == _old_peaks_to_clips(scores, 75.0)


def test_merge_gap_min_length_and_sentence_snap():
    scores = [90, 90, 10, 90, 90, 10, 10, 10, 90, 10, 10, 10, 90, 90, 90, 90]
    clips = services._peaks_to_clips(scores, 51.0, merge_gap=1, min_len=3)
    assert [(c.start_time, c.end_time) for c in clips] == [(0.0, 5.0), (12.0, 16.0)]   # 1 s gap joined; lone 1 s run dropped
    speech = [schemas.SpeechSpan(start_time=10.5, end_time=12.4), schemas.SpeechSpan(start_time=3.0, end_time=7.5)]
    snapped = services._peaks_to_clips(scores, 51.0, merge_gap=1, min_len=3, speech=speech)
    assert [(c.start_time, c.end_time) for c in snapped] == [(0.0, 7.5), (10.5, 16.0)]  # end → sentence end; start → sentence start
    far = [schemas.SpeechSpan(start_time=4.0, end_time=9.0)]                               # sentence ends 4 s after the clip: too far
    assert services._peaks_to_clips(scores, 51.0, 1, 3, far)[0].end_time == 5.0


def test_response_reports_the_clip_threshold_used(recipe, monkeypatch):
    req = schemas.HighlightRequest(video_id="vid_t", features=schemas.HighlightFeatures(
        vision_embeddings=[[0.0] * 256] * 10, audio_spectrogram_features=[[0.0] * 64] * 10))
    assert services.run_highlight(req).clip_threshold == 51.0                 # recipe tau 0.51
    monkeypatch.setattr(registry, "highlight_postproc", {})
    monkeypatch.setattr(registry, "highlight_members", [])
    assert services.run_highlight(req).clip_threshold == 75.0                 # legacy


def test_short_video_gets_scores_but_no_clips(monkeypatch):
    monkeypatch.setattr(services, "_real_highlight", lambda req: {"scores": [90.0] * 10, "clip_rules": {
        "threshold": 50.0, "merge_gap_seconds": 0, "min_clip_seconds": 3, "min_video_seconds": 120}})
    monkeypatch.setattr(services.worker_client, "is_real", lambda name: True)
    req = schemas.HighlightRequest(video_id="vid_t", features=schemas.HighlightFeatures(
        vision_embeddings=[[0.0] * 256] * 10, audio_spectrogram_features=[[0.0] * 64] * 10))
    out = services.run_highlight(req)
    assert len(out.timeline_scores) == 10 and out.recommended_clips == []
