"""AI-24 (D29-A): MiniGPT football adaptation from active cf9cfa71 + pre-registered gate vs active."""
import glob
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch

bundles = glob.glob("/kaggle/input/**/football_bundle.json", recursive=True)
news = glob.glob("/kaggle/input/**/news_manifest.json", recursive=True)
assert len(bundles) == 1 and len(news) == 1, (bundles, news)
bundle, general = Path(bundles[0]).parent, Path(news[0]).parent
with zipfile.ZipFile(bundle / "ai_core.zip") as archive:
    archive.extractall("/tmp/football_code")
sys.path.insert(0, "/tmp/football_code")

import torch
from ai_core.tests.test_gradient_check import test_rmsnorm_gradient, test_swiglu_gradient, test_mha_gradient
from ai_core.tests.test_adamw_parity import test_adamw_parity_linear_regression
from ai_core.tests.test_bpe_roundtrip import test_roundtrip_10000_sentences
from ai_core.tests.test_overfit_one_batch import test_overfit_one_batch_minigpt
from ai_core.tests.test_football_summary import test_gate_needs_a_real_football_gain_and_no_style_regression, test_football_filter_and_source_tag

torch.set_num_threads(2)
for check in (test_rmsnorm_gradient, test_swiglu_gradient, test_mha_gradient, test_adamw_parity_linear_regression,
              test_roundtrip_10000_sentences, test_gate_needs_a_real_football_gain_and_no_style_regression, test_football_filter_and_source_tag):
    check()
with patch("torch.cuda.is_available", return_value=False):
    test_overfit_one_batch_minigpt()
print("SANITY PASS", flush=True)

sha256 = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
meta = json.loads((bundle / "football_bundle.json").read_text(encoding="utf-8"))
for name, digest in meta["sha256"].items():
    assert sha256(bundle / name) == digest, name
assert meta["sha256"]["active.pt"] == "cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac"
assert torch.cuda.is_available(), "GPU required"

shard = Path("/tmp") / meta["train_shard"]["file"].split("/")[-1]
with urllib.request.urlopen(meta["train_shard"]["url"]) as response, shard.open("wb") as f:
    shutil.copyfileobj(response, f, 1 << 24)
assert shard.stat().st_size == meta["train_shard"]["size"] and sha256(shard) == meta["train_shard"]["sha256"]
print("SHARD OK", shard.name, flush=True)

data, out = Path("/tmp/football_data"), Path("/kaggle/working/football_run")
from ai_core.scripts import prepare_football_summary, finetune_news_summary, compare_football_candidate

sys.argv = ["prepare", "build", "--train-parquet", str(shard), "--football-test", str(bundle / "football_test.json"),
            "--general-test", str(general / "news_test.json"), "--general-train", str(general / "news_train.json"),
            "--output", str(data), "--limit", str(meta["limit"])]
prepare_football_summary.main()
shard.unlink()
out.mkdir(parents=True, exist_ok=True)
shutil.copy2(data / "news_manifest.json", out / "news_manifest.json")

torch.manual_seed(1337)
sys.argv = ["finetune", "--data", str(data), "--pretrain", str(bundle / "active.pt"), "--vocab", str(bundle / "bpe_vocab.json"),
            "--output", str(out)]
finetune_news_summary.main()

sys.argv = ["compare", "--data", str(data), "--vocab", str(bundle / "bpe_vocab.json"), "--active", str(bundle / "active.pt"),
            "--candidate", str(out / "minigpt/best.pt"), "--output", str(out / "gate")]
compare_football_candidate.main()
for stage in ("clean", "asr"):  # Only the selected checkpoint (copied to minigpt/) is downloaded.
    shutil.rmtree(out / stage, ignore_errors=True)
print("DONE", flush=True)
