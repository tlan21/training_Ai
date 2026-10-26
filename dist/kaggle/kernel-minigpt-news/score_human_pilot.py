"""Validate three independent human sheets against a frozen pilot or real-video packet."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=ROOT / 'data/manifests/minigpt_human_pilot.json')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    real_video = manifest.get('evaluation_kind') == 'real_video'
    packet = Path(manifest["packet"])
    samples = packet / "samples.json"
    assert hashlib.sha256(samples.read_bytes()).hexdigest() == manifest["samples_sha256"], "frozen samples changed"
    expected = {r["sample_id"] for r in json.loads(samples.read_text(encoding="utf-8"))}
    assert len(expected) == 30
    scores, by_rater, missing = [], {}, 0
    by_sample = {sample_id: [] for sample_id in sorted(expected)}
    for i in range(1, 4):
        with (packet / f"ratings_rater_{i}.csv").open(encoding="utf-8-sig") as source:
            rows = list(csv.DictReader(source))
        assert len(rows) == 30 and {r["sample_id"] for r in rows} == expected, f"rater{i}: missing/duplicate sample IDs"
        current = []
        for row in rows:
            value = row["overall_score_1_to_5"].strip()
            if not value:
                missing += 1
                continue
            score = int(value)
            assert 1 <= score <= 5, f"rater{i}/{row['sample_id']}: score must be1–5"
            current.append(score)
            by_sample[row['sample_id']].append(score)
        scores.extend(current)
        by_rater[f"rater_{i}"] = {"completed": len(current), "mean": mean(current) if len(current) == 30 else None}
    complete = missing == 0
    assert len(scores) + missing == 90
    result = {"status": ("COMPLETE — REAL VIDEO HUMAN EVALUATION" if real_video else "COMPLETE — PILOT ONLY") if complete else "PENDING — NO HUMAN MEAN ASSIGNED",
              "completed": len(scores), "required": 90, "missing": missing,
              "mean": mean(scores) if complete else None,
              "threshold_pass": mean(scores) >= 3 if complete else None,
              "raters": by_rater,
              "samples": {sample_id: {"completed": len(values), "mean": mean(values) if len(values) == 3 else None}
                          for sample_id, values in by_sample.items()},
              "video_human_DoD": ("PASS" if mean(scores) >= 3 else "FAIL") if real_video and complete else
                                  ("PENDING — 90 independent human scores required" if real_video else "NOT EVALUATED — VIVOS read-speech pilot is not video"),
              "instruction": "Each CSV must be completed by a different independent human rater."}
    if not real_video:
        result['pilot_threshold_pass'] = result['threshold_pass']
    (ROOT / manifest.get('results_file', 'docs/T1.6e_human_pilot_results.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
