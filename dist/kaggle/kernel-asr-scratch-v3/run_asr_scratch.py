"""AI-29 session 3: union + empty-target non-speech clips; continue from session-2 best.pt (kernel source), 8k steps at lr 2e-4."""
import glob
import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

root = Path('/kaggle/input')
found = glob.glob('/kaggle/input/**/scratch_manifest_v2.json', recursive=True)
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
domain = list(root.rglob('domain_audio.pack'))
assert len(domain) == 1, domain
(links / 'domain_audio.pack').symlink_to(domain[0])
(links / 'nonspeech_audio.pack').symlink_to(data / 'nonspeech_audio.pack')
public = list(root.rglob('public_audio.pack'))
assert len(public) == 1, public
(links / 'public_audio.pack').symlink_to(public[0])
payload = json.loads((data / 'scratch_manifest_v2.json').read_text(encoding='utf-8'))
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
init = [p for p in root.rglob('best.pt') if p.parent.name == 'asr_ctc' and p.parent.parent.name == 'asr_scratch']
assert len(init) == 1, init
init = init[0]
print('INIT', init, flush=True)
sys.argv = ['train_asr_scratch', '--manifest', str(manifest), '--vocab', str(data / 'robust_vocab.json'),
            '--output', '/kaggle/working/asr_scratch', '--steps', '8000', '--eval-every', '2000', '--lr', '2e-4', '--init', str(init)]
train_asr_scratch.main()
print('DONE', flush=True)
