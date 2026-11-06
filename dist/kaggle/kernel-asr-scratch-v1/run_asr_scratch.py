"""AI-29 Kaggle runner: stage the union audio, run sanity checks, train a 25.6M-param CTC ASR from scratch for one session."""
import glob
import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

root = Path('/kaggle/input')
found = glob.glob('/kaggle/input/**/scratch_manifest.json', recursive=True)
assert len(found) == 1, found
data = Path(found[0]).parent
if (data / 'ai_core.zip').exists():
    with zipfile.ZipFile(data / 'ai_core.zip') as archive:
        archive.extractall('/tmp/scratch_code')
    sys.path.insert(0, '/tmp/scratch_code')
else:  # Kaggle may auto-extract uploaded archives
    packages = [p for p in data.rglob('__init__.py') if p.parent.name == 'ai_core' and (p.parent / 'training').is_dir()]
    assert len(packages) == 1, packages
    sys.path.insert(0, str(packages[0].parent.parent))
sys.path.insert(0, str(data))
import asr_stage  # noqa: E402  (copy of run_asr_domain_replay.py: stage_audio with sha checks)

links = Path('/tmp/scratch_links')
links.mkdir()
(links / 'domain_audio.pack').symlink_to(data / 'domain_audio.pack')
public = list(root.rglob('public_audio.pack'))
assert len(public) == 1, public
(links / 'public_audio.pack').symlink_to(public[0])
payload = json.loads((data / 'scratch_manifest.json').read_text(encoding='utf-8'))
staging = Path('/tmp/scratch_stage')
staging.mkdir()
manifest = asr_stage.stage_audio(root, links, payload, staging)
print('STAGED', len(payload['items']), flush=True)

import torch  # noqa: E402
from ai_core.tests.test_gradient_check import test_rmsnorm_gradient, test_swiglu_gradient, test_mha_gradient  # noqa: E402
from ai_core.tests.test_adamw_parity import test_adamw_parity_linear_regression  # noqa: E402
from ai_core.tests.test_ctc_parity import test_ctc_loss_parity  # noqa: E402
from ai_core.tests.test_overfit_one_batch import test_overfit_one_batch_asr_ctc  # noqa: E402

for check in (test_rmsnorm_gradient, test_swiglu_gradient, test_mha_gradient, test_adamw_parity_linear_regression, test_ctc_loss_parity):
    check()
with patch('torch.cuda.is_available', return_value=False):
    test_overfit_one_batch_asr_ctc()
print('SANITY PASS', torch.cuda.get_device_name(), flush=True)

from ai_core.scripts import train_asr_scratch  # noqa: E402
sys.argv = ['train_asr_scratch', '--manifest', str(manifest), '--vocab', str(data / 'robust_vocab.json'),
            '--output', '/kaggle/working/asr_scratch', '--steps', '12000', '--eval-every', '2000']
train_asr_scratch.main()
print('DONE', flush=True)
