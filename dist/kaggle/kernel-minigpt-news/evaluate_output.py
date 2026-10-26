"""Audit the frozen News output without retraining or selecting on test results."""

import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai-core"))
from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.data.manifest import file_checksum
from ai_core.scripts.evaluate import rouge_l
from ai_core.scripts.finetune_news_summary import title_source
from ai_core.scripts.train import _pad_lm
from ai_core.tokenizer import BPETokenizer
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets.summary_dataset import SummaryPairDataset, summary_prompt_ids

BASE = Path("D:/data_training_ai/minigpt_news")
RUN = BASE / "output-v2/news_run"


def rouge_n(reference, prediction, n):
    def counts(text):
        words = text.split()
        return Counter(tuple(words[i:i+n]) for i in range(len(words)-n+1))
    ref, pred = counts(reference), counts(prediction)
    return 2 * sum((ref & pred).values()) / max(1, sum(ref.values()) + sum(pred.values()))


def main():
    assert rouge_n("a a b", "a b b", 1) == 2 / 3
    assert rouge_n("a b c", "a b c", 2) == 1
    assert rouge_n("a", "a", 2) == 0
    torch.set_num_threads(2)
    report = json.loads((RUN / "news_eval.json").read_text(encoding="utf-8"))
    predictions = [json.loads(s) for s in (RUN / "test_predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    manifest = json.loads((ROOT / "data/manifests/minigpt_news_dataset.json").read_text(encoding="utf-8"))
    assert report["dataset"]["splits"] == manifest["splits"]
    splits = {}
    for name, spec in manifest["splits"].items():
        path = BASE / "dataset" / f"news_{name}.json"
        assert file_checksum(str(path)) == spec["sha1"]
        splits[name] = json.loads(path.read_text(encoding="utf-8"))
        assert len(splits[name]) == spec["count"]
    identities = {name: {row["id"] for row in rows} for name, rows in splits.items()}
    assert not (identities["train"] & identities["val"] or identities["train"] & identities["test"] or identities["val"] & identities["test"])
    test = splits["test"]
    assert len(predictions) == len(test) == report["n_test"] == 1000
    tok = BPETokenizer.load(str(RUN / "minigpt/bpe_vocab.json"))
    scores = {system: {metric: [] for metric in ("rouge1", "rouge2", "rougeL")} for system in ("model", "lead1")}
    for row, pred in zip(test, predictions):
        assert row["id"] == pred["id"] and row["title"] == pred["reference"]
        ids = summary_prompt_ids(title_source(row), tok, "title", 512, 96)
        visible = tok.decode(ids[:-1]).removeprefix("<title> ")
        lead = re.split(r"(?<=[.!?])\s+", visible, maxsplit=1)[0].strip()
        assert lead == pred["lead1"]
        for system, text, key in (("model", pred["prediction"], "rouge_l"), ("lead1", lead, "lead1_rouge_l")):
            rl = rouge_l(row["title"], text)
            assert abs(rl - pred[key]) < 1e-12
            for metric, value in (("rouge1", rouge_n(row["title"], text, 1)),
                                  ("rouge2", rouge_n(row["title"], text, 2)), ("rougeL", rl)):
                scores[system][metric].append(value)
    means = {system: {key: float(np.mean(values)) for key, values in metrics.items()} for system, metrics in scores.items()}
    assert abs(means["model"]["rougeL"] - report["rouge_l"]) < 1e-12
    assert abs(means["lead1"]["rougeL"] - report["lead1_rouge_l"]) < 1e-12
    delta = np.array(scores["model"]["rougeL"]) - scores["lead1"]["rougeL"]
    rng = np.random.default_rng(1337)
    ci = np.quantile([rng.choice(delta, len(delta), replace=True).mean() for _ in range(2000)], [.025, .975])
    assert np.allclose(ci, report["delta_ci95"], atol=1e-12)
    val = [json.loads(s) for s in (RUN / "validation.jsonl").read_text().splitlines()]
    checkpoint = RUN / "minigpt/best.pt"
    assert file_checksum(str(checkpoint)) == report["checkpoint_sha1"]
    ckpt = load_checkpoint(str(checkpoint))
    assert ckpt["metadata"]["stage"] == report["selected_stage"] == "asr"
    assert ckpt["metrics"]["step"] == report["selected_step"] == 3000
    assert ckpt["bpe_vocab"] == json.loads((RUN / "minigpt/bpe_vocab.json").read_text())
    assert file_checksum(str(checkpoint)) == file_checksum(str(RUN / "asr/minigpt/best.pt"))
    for stage, expected_steps in (("clean", 16000), ("asr", 4000)):
        last = load_checkpoint(str(RUN / stage / "minigpt/last.pt"))
        assert last["metrics"]["step"] == expected_steps
        best = load_checkpoint(str(RUN / stage / "minigpt/best.pt"))
        values = [(row["clean_rouge_l"] + row["asr_rouge_l"]) / 2 for row in val if row["stage"] == stage]
        assert abs(max(values) - best["metrics"]["rouge_l"]) < 1e-12
    cfg = ModelConfig(**ckpt["config"])
    assert (cfg.d_model, cfg.n_layers, cfg.n_heads, cfg.vocab_size, cfg.context_len) == (384, 6, 6, 8192, 1024)
    model = build_model("minigpt", cfg).eval()
    model.load_state_dict(ckpt["state_dict"], strict=True)
    assert all(bool(torch.isfinite(p).all()) for p in model.parameters())
    ds = SummaryPairDataset([(title_source(r), r["title"]) for r in test], tok, context_len=512, max_target_tokens=96)
    total_loss, tokens = 0., 0
    with torch.inference_mode():
        for x, y in DataLoader(ds, batch_size=8, collate_fn=_pad_lm):
            logits, _ = model(x)
            total_loss += torch.nn.functional.cross_entropy(logits.reshape(-1, cfg.vocab_size), y.reshape(-1),
                                                            ignore_index=-100, reduction="sum").item()
            tokens += int(y.ne(-100).sum())
    smoke = []
    with torch.inference_mode():
        for fmt, source in (("title", title_source(test[0])), ("sum", test[0]["body"]), ("cap", title_source(test[0]))):
            ids = summary_prompt_ids(source, tok, fmt, 512, 96)
            generated = model.generate(torch.tensor([ids]), 96, temperature=0, eos_id=tok.special_tokens["<eos>"])
            text = tok.decode(generated[0, len(ids):].tolist())
            assert text.strip()
            smoke.append({"format": fmt, "text": text, "input_id": test[0]["id"], "device": "CPU fp32"})
    result = {"date": "2026-10-15", "status": "AUTOMATIC ROUGE-L PASS; HUMAN/DEPLOYMENT PENDING",
              "checks": "1000 IDs/references/Lead1/scores, split SHA1/group disjointness, best-val selection, checkpoint/BPE/config/finite weights verified",
              "metrics": means, "rougeL_delta": float(delta.mean()), "paired_bootstrap_ci95": ci.tolist(),
              "wins_ties_losses": [int((delta > 0).sum()), int((delta == 0).sum()), int((delta < 0).sum())],
              "zero_rougeL_count": int(np.count_nonzero(np.array(scores["model"]["rougeL"]) == 0)),
              "empty_prediction_count": sum(not r["prediction"].strip() for r in predictions),
              "exact_title_matches": sum(r["prediction"] == r["reference"] for r in predictions),
              "test_target_perplexity_cpu_fp32": math.exp(total_loss / tokens), "test_target_tokens": tokens,
              "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
              "checkpoint_path": str(checkpoint), "selected_stage": "asr", "selected_step": 3000,
              "smoke": smoke, "first_five_predictions": predictions[:5]}
    (ROOT / "docs/T1.6c_news_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("first_five_predictions",)}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
