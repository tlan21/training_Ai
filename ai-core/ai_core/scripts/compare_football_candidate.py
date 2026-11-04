"""AI-24 (D29-A) pre-registered gate: candidate vs active MiniGPT on football test1000 and general test1000.

Gate (coordination/claude/TASKS.md AI-24), test sets scored once after validation-only checkpoint selection:
1. football `sum` clean and noisy: candidate > active, paired CI95 lower bound of (candidate - active) > 0;
   noisy also candidate > Lead-1 (v2, user 2026-11-04: clean > Lead-1 dropped — active fails it too; product input is ASR text);
2. general `sum`/`title` and football `title`, clean and noisy: candidate >= active - 0.005;
3. `sum` clean on both sets: repeated-trigram fraction and cap-hit rate <= active + 0.01.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from .. import build_model
from ..config import ModelConfig
from ..data.manifest import file_checksum
from ..tokenizer import BPETokenizer
from ..training.checkpoint import load_checkpoint
from .finetune_news_summary import evaluate, mean

GUARD = 0.005
STYLE = 0.01


def load(path, device):
    ckpt = load_checkpoint(str(path))
    model = build_model("minigpt", ModelConfig(**ckpt["config"]))
    model.load_state_dict(ckpt["state_dict"])
    return model.to(device)


def paired_ci(a, b):
    delta = np.array([x["rouge_l"] - y["rouge_l"] for x, y in zip(a, b)])
    rng = np.random.default_rng(1337)
    return float(delta.mean()), np.quantile([rng.choice(delta, len(delta)).mean() for _ in range(2000)], [.025, .975]).tolist()


def gate(scores):
    """scores[(set, fmt, noisy)] = {"active": rows, "candidate": rows}; returns per-check results and overall pass."""
    checks = {}
    for noisy in (False, True):
        cand, act = scores[("football", "sum", noisy)]["candidate"], scores[("football", "sum", noisy)]["active"]
        delta, ci = paired_ci(cand, act)
        checks[f"1_football_sum_{'noisy' if noisy else 'clean'}"] = {
            "candidate": mean(cand, "rouge_l"), "active": mean(act, "rouge_l"), "lead1": mean(cand, "lead1_rouge_l"),
            "delta": delta, "ci95": ci,
            "pass": (not noisy or mean(cand, "rouge_l") > mean(cand, "lead1_rouge_l")) and delta > 0 and ci[0] > 0}
    for key in [("general", "sum"), ("general", "title"), ("football", "title")]:
        for noisy in (False, True):
            s = scores[(*key, noisy)]
            c, a = mean(s["candidate"], "rouge_l"), mean(s["active"], "rouge_l")
            checks[f"2_{key[0]}_{key[1]}_{'noisy' if noisy else 'clean'}"] = {"candidate": c, "active": a, "pass": c >= a - GUARD}
    for name in ("football", "general"):
        s = scores[(name, "sum", False)]
        for metric in ("repeated_trigram_fraction", "cap_hit"):
            c, a = mean(s["candidate"], metric), mean(s["active"], metric)
            checks[f"3_{name}_sum_{metric}"] = {"candidate": c, "active": a, "pass": c <= a + STYLE}
    return checks, all(v["pass"] for v in checks.values())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", required=True, help="prepare_football_summary build output (news_test.json, general_test.json)")
    p.add_argument("--vocab", required=True)
    p.add_argument("--active", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data = Path(args.data)
    sets = {"football": json.loads((data / "news_test.json").read_text(encoding="utf-8")),
            "general": json.loads((data / "general_test.json").read_text(encoding="utf-8"))}
    tok = BPETokenizer.load(args.vocab)
    scores = {}
    for role, path in (("active", args.active), ("candidate", args.candidate)):
        model = load(path, device)
        for name, rows in sets.items():
            for fmt in ("sum", "title"):
                for noisy in (False, True):
                    scores.setdefault((name, fmt, noisy), {})[role] = evaluate(model, rows, tok, device, noisy=noisy, fmt=fmt)
                    print(role, name, fmt, "noisy" if noisy else "clean", mean(scores[(name, fmt, noisy)][role], "rouge_l"), flush=True)
        del model
    checks, passed = gate(scores)
    sha256 = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    report = {"active_sha256": sha256(args.active), "candidate_sha256": sha256(args.candidate),
              "data_manifest_sha1": file_checksum(str(data / "news_manifest.json")),
              "checks": checks, "gate_pass": passed,
              "human_evaluation": "PENDING: 30 real ASR transcripts, 3 raters, mean >=3/5 (not replaced by this gate)"}
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "football_gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "football_gate_predictions.jsonl").open("w", encoding="utf-8") as f:
        for (name, fmt, noisy), roles in scores.items():
            for role, rows in roles.items():
                f.write(json.dumps({"set": name, "fmt": fmt, "noisy": noisy, "role": role, "rows": rows}, ensure_ascii=False) + "\n")
    print("GATE", json.dumps({"gate_pass": passed, "checks": {k: v["pass"] for k, v in checks.items()}}), flush=True)


if __name__ == "__main__":
    main()
