"""AI-12 — verify a Codex INT-13 bundle BEFORE any training/evaluation (read-only, no model).

  python -m ai_core.scripts.verify_ttv2_bundle D:/video-ai-exports/ttv2/<ts> --out report.json

Fails loudly on version / provenance / sha256 / row count / schema; otherwise reports every reject reason
(zeros included), label counts, the time split and the D19 data stage.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from ..training.datasets import product_interactions as pi


def verify(directory, eval_fraction: float = 0.2) -> dict:
    export = pi.load_export(directory)
    manifest = json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))
    cleaned = pi.clean(export)
    labels = pi.label(cleaned)
    n_pos = Counter(l.user_id for l in labels if l.positive)
    report = {
        "export_version": pi.EXPORT_VERSION, "label_version": pi.LABEL_VERSION,
        "snapshot_at": manifest["snapshot_at"], "provenance": export.provenance,
        "rows": {name: meta["rows"] for name, meta in manifest["files"].items()},
        "sha256": {name: meta["sha256"] for name, meta in manifest["files"].items()},
        "dropped": {reason: cleaned.dropped.get(reason, 0) for reason in (*pi.REJECT_REASONS, "duplicate")},
        "valid_interactions": len(cleaned.interactions),
        "users_with_valid_interactions": len({r["user_id"] for r in cleaned.interactions}),
        "labels": {"positive": sum(l.positive for l in labels), "negative": sum(not l.positive for l in labels)},
        "category_vocab": pi.category_vocab(export).version,
    }
    split = pi.time_split(labels, eval_fraction) if labels else None
    eval_users = {l.user_id for l in split.eval if l.positive} if split else set()
    report["split"] = None if split is None else {
        "cutoff": split.cutoff.isoformat(), "train": len(split.train), "eval": len(split.eval),
        "eval_users": len(eval_users), "cold_start_users": len(split.cold_start_users)}
    report["eval_users_with_5_pos"] = sum(1 for u in eval_users if n_pos[u] >= 5)
    report["stage"] = pi.gate_stage(report["users_with_valid_interactions"], report["valid_interactions"],
                                    report["eval_users_with_5_pos"])
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("--out")
    ap.add_argument("--eval-fraction", type=float, default=0.2)
    args = ap.parse_args()
    text = json.dumps(verify(args.bundle, args.eval_fraction), ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
