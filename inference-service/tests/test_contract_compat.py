"""D20: the current API must stay backward compatible with the released contracts (snapshots from master).
AI-15: v1.3 snapshot added — /v2 (D24) is additive. AI-23 (AI-API v3.0, D24 step 3): v1.5 snapshot added; the ONLY allowed
removals are the four /v1 paths deprecated in v1.5 (Codex RE:HC-17: no caller left) and the schemas used only by them."""
import json
from pathlib import Path

import pytest

from app.main import app

API = Path(__file__).resolve().parents[2] / "coordination/claude/api"
SNAPSHOTS = {v: json.loads((API / f"inference_openapi_{v}.json").read_text(encoding="utf-8")) for v in ("v1.2", "v1.3", "v1.5")}
NEW = app.openapi()
# Deliberate v1.3 change (D18): fake metadata removed, fields kept but nullable. Clients reading strings get "".
ALLOWED_NULLABLE = {("Recommendation", "title"), ("Recommendation", "thumbnail_url")}
REMOVED_V3_PATHS = {"/v1/vision/completions", "/v1/asr/completions", "/v1/search/completions", "/v1/recommendation/completions"}
REMOVED_V3_SCHEMAS = {"VisionRequest", "VisionResponse", "ASRRequest", "SearchRequest", "SearchResponse", "SearchResult",
                      "RecommendationRequest", "RecommendationResponse", "Recommendation"}


def _request_models(spec):
    refs = set()
    for ops in spec["paths"].values():
        for op in ops.values():
            ref = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {}).get("$ref")
            if ref:
                refs.add(ref.rsplit("/", 1)[1])
    return refs


def _type(prop):
    return prop.get("type") or tuple(sorted(json.dumps(p, sort_keys=True) for p in prop.get("anyOf", [])))


@pytest.mark.parametrize("version", SNAPSHOTS)
def test_no_path_or_method_removed(version):
    OLD = SNAPSHOTS[version]
    for path, ops in OLD["paths"].items():
        if path in REMOVED_V3_PATHS:
            assert path not in NEW["paths"], path
            continue
        assert path in NEW["paths"], path
        assert set(ops) <= set(NEW["paths"][path]), path


@pytest.mark.parametrize("version", SNAPSHOTS)
def test_schemas_only_grow(version):
    OLD = SNAPSHOTS[version]
    old_s, new_s = OLD["components"]["schemas"], NEW["components"]["schemas"]
    requests = _request_models(OLD)
    for name, old in old_s.items():
        if name in REMOVED_V3_SCHEMAS:
            continue
        new = new_s[name]
        for prop, spec in old.get("properties", {}).items():
            assert prop in new["properties"], f"{name}.{prop} removed"
            if _type(spec) != _type(new["properties"][prop]):
                assert (name, prop) in ALLOWED_NULLABLE, f"{name}.{prop} type changed"
                assert {"type": "null"} in new["properties"][prop].get("anyOf", []), f"{name}.{prop} must only become nullable"
        if name in requests:  # a new required request field would break existing callers
            assert set(new.get("required", [])) <= set(old.get("required", [])), f"{name} gained required fields"


def test_v3_removals_were_deprecated_first():
    """Nothing disappears without a release that announced it: every removed path is deprecated in the v1.5 snapshot."""
    v15 = SNAPSHOTS["v1.5"]["paths"]
    assert all(op.get("deprecated") for path in REMOVED_V3_PATHS for op in v15[path].values())
