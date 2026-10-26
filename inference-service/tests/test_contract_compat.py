"""D20: the current API must stay backward compatible with the released v1.2 contract (snapshot from master)."""
import json
from pathlib import Path

from app.main import app

OLD = json.loads((Path(__file__).resolve().parents[2] / "coordination/claude/api/inference_openapi_v1.2.json").read_text(encoding="utf-8"))
NEW = app.openapi()
# Deliberate v1.3 change (D18): fake metadata removed, fields kept but nullable. Clients reading strings get "".
ALLOWED_NULLABLE = {("Recommendation", "title"), ("Recommendation", "thumbnail_url")}


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


def test_no_path_or_method_removed():
    for path, ops in OLD["paths"].items():
        assert path in NEW["paths"], path
        assert set(ops) <= set(NEW["paths"][path]), path


def test_schemas_only_grow():
    old_s, new_s = OLD["components"]["schemas"], NEW["components"]["schemas"]
    requests = _request_models(OLD)
    for name, old in old_s.items():
        new = new_s[name]
        for prop, spec in old.get("properties", {}).items():
            assert prop in new["properties"], f"{name}.{prop} removed"
            if _type(spec) != _type(new["properties"][prop]):
                assert (name, prop) in ALLOWED_NULLABLE, f"{name}.{prop} type changed"
                assert {"type": "null"} in new["properties"][prop].get("anyOf", []), f"{name}.{prop} must only become nullable"
        if name in requests:  # a new required request field would break existing callers
            assert set(new.get("required", [])) <= set(old.get("required", [])), f"{name} gained required fields"
