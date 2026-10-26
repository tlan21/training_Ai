import glob, os, sys, zipfile
from pathlib import Path
bundle = glob.glob("/kaggle/input/**/news_manifest.json", recursive=True)
assert len(bundle) == 1, "Expected exactly one frozen News dataset"
data = Path(bundle[0]).parent
if (data / "ai_core.zip").exists():
    with zipfile.ZipFile(data / "ai_core.zip") as z:
        z.extractall("/tmp/news_code")
    sys.path.insert(0, "/tmp/news_code")
else:
    packages = [p for p in data.rglob("__init__.py") if p.parent.name == "ai_core" and (p.parent / "training").is_dir()]
    assert len(packages) == 1, "Expected one auto-extracted ai_core package"
    sys.path.insert(0, str(packages[0].parent.parent))
print("bundle", data, flush=True)
from ai_core.tests.test_gradient_check import test_rmsnorm_gradient, test_swiglu_gradient, test_mha_gradient
from ai_core.tests.test_adamw_parity import test_adamw_parity_linear_regression
from ai_core.tests.test_overfit_one_batch import test_overfit_one_batch_minigpt
from ai_core.tests.test_bpe_roundtrip import test_roundtrip_10000_sentences
import torch
torch.set_num_threads(2)
for fn in (test_rmsnorm_gradient, test_swiglu_gradient, test_mha_gradient): fn()
print("SANITY gradient <1e-4 PASS", flush=True)
test_adamw_parity_linear_regression()
print("SANITY AdamW parity <1e-6 PASS", flush=True)
test_roundtrip_10000_sentences()
print("SANITY BPE 10000/10000 roundtrip PASS", flush=True)
from unittest.mock import patch
with patch("torch.cuda.is_available", return_value=False):
    test_overfit_one_batch_minigpt()
print("SANITY MiniGPT one-batch loss <0.05 PASS", flush=True)
from ai_core.scripts.finetune_news_summary import main
sys.argv = ["finetune_news_summary", "--data", str(data), "--pretrain", str(data / "pretrain.pt"), "--vocab", str(data / "bpe_vocab.json"), "--output", "/kaggle/working/news_run"]
main()
