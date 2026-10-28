"""AI-03c (D22): mixed clean/ASR News replay + 29 Claude-reviewed real-video summary pairs; same non-regression guard."""
import glob
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

bundles = glob.glob('/kaggle/input/**/news_manifest.json',recursive=True)
assert len(bundles)==1, 'Expected exactly one aligned dataset'
data = Path(bundles[0]).parent
if (data/'ai_core.zip').exists():
    with zipfile.ZipFile(data/'ai_core.zip') as archive:
        archive.extractall('/tmp/aligned_code')
    sys.path.insert(0,'/tmp/aligned_code')
else:
    packages = [p for p in data.rglob('__init__.py') if p.parent.name=='ai_core' and (p.parent/'training').is_dir()]
    assert len(packages)==1, 'Expected one extracted own ai_core package'
    sys.path.insert(0,str(packages[0].parent.parent))

import torch
from unittest.mock import patch
from ai_core.tests.test_gradient_check import test_rmsnorm_gradient,test_swiglu_gradient,test_mha_gradient
from ai_core.tests.test_adamw_parity import test_adamw_parity_linear_regression
from ai_core.tests.test_bpe_roundtrip import test_roundtrip_10000_sentences
from ai_core.tests.test_overfit_one_batch import test_overfit_one_batch_minigpt
from ai_core.scripts.finetune_news_summary import main,aligned_validation,validate_aligned_bundle
from ai_core.tokenizer import BPETokenizer
from ai_core.training.checkpoint import load_checkpoint
from ai_core.config import ModelConfig
from ai_core import build_model

torch.set_num_threads(2)
for check in (test_rmsnorm_gradient,test_swiglu_gradient,test_mha_gradient):check()
print('SANITY gradient <1e-4 PASS',flush=True)
test_adamw_parity_linear_regression()
print('SANITY AdamW <1e-6 PASS',flush=True)
test_roundtrip_10000_sentences()
print('SANITY BPE10000/10000 PASS',flush=True)
with patch('torch.cuda.is_available',return_value=False):test_overfit_one_batch_minigpt()
print('SANITY MiniGPT toy1batch loss<0.05 PASS',flush=True)

manifest = json.loads((data/'news_manifest.json').read_text(encoding='utf-8'))
train = json.loads((data/'news_train.json').read_text(encoding='utf-8'))
val = json.loads((data/'news_val.json').read_text(encoding='utf-8'))
assert len(train)==956 and len(val)==64
validate_aligned_bundle(data,manifest,train,val)
domain_sha = hashlib.sha256((data/'domain_train.json').read_bytes()).hexdigest()
assert domain_sha.startswith('8467eaa434e3'), domain_sha
assert len(json.loads((data/'domain_train.json').read_text(encoding='utf-8')))==29
init_sha = hashlib.sha256((data/'pretrain.pt').read_bytes()).hexdigest()
assert init_sha=='cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac'
assert torch.cuda.is_available(), 'GPU required'
torch.manual_seed(1337)
torch.cuda.reset_peak_memory_stats()
started, completed = time.time(), False
try:
    saved = load_checkpoint(str(data/'pretrain.pt'))
    model = build_model('minigpt',ModelConfig(**saved['config']))
    model.load_state_dict(saved['state_dict'],strict=True)
    model = model.eval().cuda()
    tok = BPETokenizer.load(str(data/'bpe_vocab.json'))
    score,metrics,predictions = aligned_validation(model,val,tok,torch.device('cuda'))
    baseline = {'init_sha256':init_sha,'data_manifest_sha256':hashlib.sha256((data/'news_manifest.json').read_bytes()).hexdigest(),
                'n_val':64,'eval_precision':'fp16_autocast','selection_score':score,'metrics':metrics,'predictions':predictions}
    Path('/kaggle/working/replay_baseline.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SAME_GPU_BASELINE',score,json.dumps(metrics),flush=True)
    del model,saved,predictions,train
    torch.cuda.empty_cache()
    sys.argv = ['finetune_news_summary','--data',str(data),'--pretrain',str(data/'pretrain.pt'),
                '--vocab',str(data/'bpe_vocab.json'),'--output','/kaggle/working/replay_run',
                '--mixed-replay','--baseline','/kaggle/working/replay_baseline.json',
                '--domain',str(data/'domain_train.json'),'--domain-repeat','8']
    main()
    completed = True
finally:
    torch.cuda.synchronize()
    allocated = torch.cuda.max_memory_allocated()/1024**3
    reserved = torch.cuda.max_memory_reserved()/1024**3
    runtime = {'completed':completed,'gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,
               'seed':1337,'elapsed_seconds':time.time()-started,
               'peak_allocated_gib':allocated,'peak_reserved_gib':reserved,
               'scope':'same-GPU baseline + candidate training/validation; not six-model inference',
               'train_8gib_pass':allocated<=8 and reserved<=8}
    Path('/kaggle/working/replay_runtime.json').write_text(json.dumps(runtime,indent=2))
    print('RUNTIME',json.dumps(runtime),flush=True)
    if completed:
        assert runtime['train_8gib_pass'], 'Training VRAM exceeded8GiB'
