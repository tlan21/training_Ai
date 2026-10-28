"""AI-03c: generate MiniGPT outputs for the 40 domain clips x 2 inputs through the production service code (CPU).

  python eval_local.py <candidate best.pt> <out.json>
Builds a temporary checkpoint dir = canonical checkpoints with only minigpt replaced; the canonical dir is never touched.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = Path("D:/data_training_ai/minigpt_domain_v1_20261019")
REVIEW = DOMAIN / "claude_review_d22_v1/claude_reviewed_summaries_v1.json"


def main(candidate, out):
    tmp = Path(tempfile.mkdtemp(prefix="ai03c_ckpt_", dir="D:/tmp"))
    for model in ("vit", "siamese", "asr_ctc", "highlight_fusion", "two_tower", "minigpt"):
        (tmp / model).mkdir()
        src = Path(candidate) if model == "minigpt" else ROOT / "ai-core/checkpoints" / model / "best.pt"
        shutil.copy2(src, tmp / model / "best.pt")
    shutil.copy2(ROOT / "ai-core/checkpoints/minigpt/bpe_vocab.json", tmp / "minigpt/bpe_vocab.json")
    os.environ.update(CHECKPOINT_DIR=str(tmp), FORCE_STUB="0", AI_SERVICE_KEY="local")
    sys.path[:0] = [str(ROOT / "inference-service"), str(ROOT / "ai-core")]
    from app.registry import registry
    from app import schemas, services
    registry.load_all()
    assert not registry.stub_mode, registry.load_error
    samples = {x["sample_id"]: x for x in json.loads((DOMAIN / "samples.json").read_text(encoding="utf-8"))}
    review = {x["sample_id"]: x for x in json.loads(REVIEW.read_text(encoding="utf-8"))["records"]}
    rows = []
    for sid in sorted(samples):
        row = {"sample_id": sid, "split": samples[sid]["split"], "reference": review[sid]["summary"], "review": review[sid]["review"]}
        for name, text in (("clean", review[sid]["transcript"]), ("asr_active", samples[sid]["asr_inputs"]["active"]["text"])):
            r = services.run_completion(schemas.CompletionRequest(prompt=text, max_tokens=96, temperature=0))
            row[name] = {"input": text, "output": r.choices[0].text}
        rows.append(row)
    Path(out).write_text(json.dumps({"model": str(candidate), "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(tmp)
    print(len(rows), "clips ->", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
