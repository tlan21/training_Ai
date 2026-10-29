"""AI-19: the 256-d vision features served to Highlight Fusion must equal the ones it was TRAINED on
(ai_core.scripts.extract_vit_embeddings with the siamese checkpoint). Real checkpoints; skipped when absent."""
import io
from pathlib import Path

import pytest
import torch
from PIL import Image

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.extract_vit_embeddings import _load_image
from ai_core.training.checkpoint import load_checkpoint
from app import worker
from app.registry import registry

CKPT = Path(__file__).resolve().parents[2] / "ai-core/checkpoints"
pytestmark = pytest.mark.skipif(not (CKPT / "siamese/best.pt").exists() or not (CKPT / "vit/best.pt").exists(),
                                reason="real vit/siamese checkpoints not present")


def _model(name):
    ckpt = load_checkpoint(str(CKPT / name / "best.pt"), map_location="cpu")
    model = build_model(ckpt["config"].get("name", name), ModelConfig(**ckpt["config"])).eval()
    model.load_state_dict(ckpt["state_dict"])
    return model


def test_served_highlight_features_equal_training_features(tmp_path, monkeypatch):
    vit, siamese = _model("vit"), _model("siamese")
    monkeypatch.setattr(registry, "models", {"vit": vit, "siamese": siamese})
    monkeypatch.setattr(registry, "device", "cpu")
    paths, frames = [], []
    for i in range(3):
        buf = io.BytesIO()
        Image.new("RGB", (398, 224), (60 * i, 120, 200 - 50 * i)).save(buf, "JPEG")
        (tmp_path / f"{i:08d}.jpg").write_bytes(buf.getvalue())
        paths.append(tmp_path / f"{i:08d}.jpg")
        frames.append(buf.getvalue())
    _, served, _ = worker.vision(frames)
    with torch.no_grad():                                   # exactly extract_vit_embeddings' path (backbone of the siamese checkpoint)
        _, trained = siamese.backbone(torch.stack([_load_image(str(p), 224) for p in paths]), return_embedding=True)
    assert torch.allclose(torch.tensor(served), trained, atol=1e-4)
    with torch.no_grad():
        _, classifier = vit(torch.stack([_load_image(str(p), 224) for p in paths]), return_embedding=True)
    assert not torch.allclose(torch.tensor(served), classifier, atol=1e-1)   # the bug: classifier embedding is a different space
