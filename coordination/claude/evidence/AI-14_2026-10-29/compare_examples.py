"""Compare two example dirs ignoring volatile fields (id/created/execution time/ thumbnail paths)."""
import json, sys, pathlib
VOLATILE = {"id", "created", "query_metadata", "execution_time_ms"}
def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x
a, b = map(pathlib.Path, sys.argv[1:3])
for p in sorted(a.glob("*.json")):
    q = b / p.name
    if not q.exists():
        print(f"{p.name}: missing in {b}"); continue
    x, y = strip(json.loads(p.read_text(encoding="utf-8"))), strip(json.loads(q.read_text(encoding="utf-8")))
    print(f"{p.name}: {'SAME' if x == y else 'DIFF'}")
