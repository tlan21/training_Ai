"""AI-09 / D14: MovieLens Two-Tower export must stay in the sandbox and never look like product IDs."""
from pathlib import Path

import pytest
import torch

from ai_core.scripts import export_two_tower_milvus as ex

ROOT = Path(__file__).resolve().parents[3]
CKPT = ROOT / "ai-core/checkpoints/two_tower/best.pt"
DATA = ROOT / "dist/kaggle/ai-core-ds"


def test_vector_ids_are_namespaced_not_product_ids():
    ids = [ex.vector_id("user", 1), ex.vector_id("video", 1682)]
    assert ids == ["ml100k_u_1", "ml100k_i_1682"]
    assert not any(i.startswith(("usr_", "vid_")) for i in ids) and all(len(i) <= 50 for i in ids)


def test_product_collection_is_refused():
    with pytest.raises(SystemExit, match="D14"):
        ex.check_target(ex.PRODUCT_COLLECTION)
    ex.check_target(ex.SANDBOX_COLLECTION)


def test_delete_expression_only_touches_own_namespace():
    assert ex.DELETE_EXPR == 'id like "ml100k_%"'


@pytest.mark.skipif(not (CKPT.exists() and (DATA / "u.data").exists()), reason="needs active checkpoint + MovieLens files")
def test_build_vectors_matches_checkpoint_vocabulary_and_manifest():
    ids, vectors, types, ckpt = ex.build_vectors(str(CKPT), str(DATA / "u.data"), str(DATA / "u.item"))
    assert types.count("user") == 942 and types.count("video") == 1682
    assert vectors.shape == (942 + 1682, 128) and torch.isfinite(vectors).all()
    assert torch.allclose(vectors.norm(dim=-1), torch.ones(len(ids)), atol=1e-4)
    assert len(set(ids)) == len(ids) and all(i.startswith("ml100k_") for i in ids)
    man = ex.artifact_manifest(str(CKPT), str(DATA / "u.data"), str(DATA / "u.item"), ids, types, ckpt)
    assert man["checkpoint_sha256"].startswith("f28c3794")
    assert man["encoder_input"]["user"]["dim"] == 942 and man["encoder_input"]["video"]["dim"] == 1702
    assert man["product_ids_supported"] is False
