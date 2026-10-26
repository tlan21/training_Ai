"""Verify the local News HTTP path against direct model generation and a >1024-token input."""

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai-core"))
from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.tokenizer import BPETokenizer
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets.summary_dataset import summary_prompt_ids


def main():
    torch.set_num_threads(2)
    folder = ROOT / "ai-core/checkpoints/minigpt"
    checkpoint = folder / "best.pt"
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    assert digest == "cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac"
    ckpt = load_checkpoint(str(checkpoint))
    model = build_model("minigpt", ModelConfig(**ckpt["config"])).eval()
    model.load_state_dict(ckpt["state_dict"])
    tok = BPETokenizer.load(str(folder / "bpe_vocab.json"))
    key = next(line.partition("=")[2].strip().strip('"\'') for line in (ROOT / ".env").read_text().splitlines()
               if line.strip().startswith("AI_SERVICE_KEY="))

    def request(data, auth=True):
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = "Bearer " + key
        req = urllib.request.Request("http://127.0.0.1:8001/v1/completions", data=json.dumps(data).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=240) as r:
            return json.load(r)

    source = "Hôm nay đội bóng thành phố tổ chức một buổi tập chuẩn bị cho trận đấu cuối tuần. Huấn luyện viên cho các cầu thủ tập chuyền bóng và dứt điểm."
    records = []
    with torch.inference_mode():
        for fmt in ("sum", "title", "cap"):
            ids = summary_prompt_ids(source, tok, fmt, 512, 96)
            direct = model.generate(torch.tensor([ids]), 96, temperature=0, eos_id=tok.special_tokens["<eos>"])
            expected = tok.decode(direct[0, len(ids):].tolist()).strip()
            started = time.monotonic()
            response = request({"prompt": f"<{fmt}> " + source, "max_tokens": 256, "temperature": 0})
            actual = response["choices"][0]["text"]
            assert actual == expected and actual.strip(), f"{fmt}: HTTP/direct mismatch"
            records.append({"format": fmt, "http_direct_parity": True, "text": actual,
                            "seconds": time.monotonic() - started})
    raw = request({"prompt": source, "max_tokens": 256, "temperature": 0})
    assert raw["choices"][0]["text"] == records[0]["text"]
    upper = request({"prompt": source.upper(), "temperature": 0})
    lower = request({"prompt": source.lower(), "temperature": 0})
    assert upper["choices"][0]["text"] == lower["choices"][0]["text"]
    long_source = source * 35
    tokens = len(tok.encode(long_source))
    assert tokens > 1024
    started = time.monotonic()
    long_result = request({"prompt": long_source, "max_tokens": 256, "temperature": 0})
    long_elapsed = time.monotonic() - started
    assert long_result["choices"][0]["text"].strip()
    assert request({"prompt": "  ", "temperature": 0})["choices"][0]["text"] == ""
    for data, auth, status in (({"prompt": source}, False, 401), ({"prompt": source, "max_tokens": 0}, True, 422)):
        try:
            request(data, auth=auth)
            raise AssertionError("expected rejection")
        except urllib.error.HTTPError as exc:
            assert exc.code == status
    health = json.load(urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=30))
    assert not health["stub_mode"] and not health["degraded"] and len(health["models_loaded"]) == 6
    result = {"date": "2026-10-15", "status": "PASS — LOCAL CPU", "checkpoint_sha256": digest,
              "profile": {"context": 512, "reserve": 96, "format": "<format> source <eos>; no BOS"},
              "short_formats": records, "raw_defaults_to_sum": True,
              "uppercase_ctc_normalized": True,
              "long_input_tokens": tokens, "long_result": long_result["choices"][0]["text"],
              "long_elapsed_seconds": long_elapsed, "silence_no_hallucination": True,
              "missing_auth_401": True, "invalid_budget_422": True, "health": health,
              "limitation": "Structural integration test with repeated synthetic text; not a quality evaluation"}
    (ROOT / "docs/T1.6e_inference_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("short_formats", "long_result")}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
