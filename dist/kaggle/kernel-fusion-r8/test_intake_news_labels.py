"""AI-19 intake: per-second labels, boundary IGNORE, strict rejection of non-human or mismatched exports."""
import importlib.util
from pathlib import Path

import pytest
import torch

spec = importlib.util.spec_from_file_location("intake", Path(__file__).with_name("intake_news_labels.py"))
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)

PROPOSALS = {"videos": {"vid_a": {"duration": 30, "source_sha256": "aa"}}}


def _export(**over):
    v = {"video_id": "vid_a", "source_sha256": "aa", "status": "HUMAN_VERIFIED", "segments": [{"start": 5, "end": 12, "origin": "HUMAN"}]}
    v.update(over)
    return {"schema": "highlight-labels-v1", "rater": "khoa", "exported_at": "2026-10-29T12:00:00Z", "videos": [v]}


def test_labels_one_inside_zero_outside_ignore_at_edges():
    y = intake.per_second_labels([{"start": 5, "end": 12}], 20)
    assert y[:4].tolist() == [0, 0, 0, 0] and y[6:11].tolist() == [1] * 5 and y[13:].tolist() == [0] * 7
    assert y[4].item() == y[5].item() == y[11].item() == y[12].item() == -1


def test_valid_export_passes():
    assert intake.validate(_export(), PROPOSALS) == []


@pytest.mark.parametrize("over, needle", [
    ({"status": "CLAUDE_PROPOSED"}, "HUMAN_VERIFIED"),
    ({"source_sha256": "bb"}, "SHA-256"),
    ({"segments": [{"start": 5, "end": 40}]}, "outside"),
    ({"segments": [{"start": 5, "end": 12}, {"start": 10, "end": 15}]}, "overlap"),
    ({"video_id": "vid_x"}, "not one of"),
])
def test_bad_exports_are_rejected(over, needle):
    assert any(needle in e for e in intake.validate(_export(**over), PROPOSALS))


def test_missing_rater_rejected():
    e = _export()
    e["rater"] = " "
    assert any("rater" in x for x in intake.validate(e, PROPOSALS))
