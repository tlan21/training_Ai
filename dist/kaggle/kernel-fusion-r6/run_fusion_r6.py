"""Highlight Fusion VONG 6 (AI-17): chong overfit — chuan hoa dac trung theo tung video + augment train.

Kernel MOI (khong dung ai-core-fusion-140): Kaggle chi giu output ban moi nhat moi kernel, output vong 5 phai con.
Dang ky truoc: .claude/evaluation_plan.md §2.1 "Vong 6". Cung split vong 5 (218/28/27), d_model 128 / dropout 0.3 / 4000 step.
Sweep seed 1337 tren VAL: {norm 0/1} x {aug 0/1}; bien the val F1 tho cao nhat -> them seed 1338, 1339.
TAP TEST KHONG XUAT HIEN O DAY. Cham local (stride 30, gop seed, k+tau tren val), test sau khi quyet.
"""

import glob
import json
import os
import shutil
import sys
import time
import zipfile

sys.path.insert(0, '/kaggle/working')
if not glob.glob('/kaggle/working/ai_core'):
    z = glob.glob('/kaggle/input/**/ai_core.zip', recursive=True)
    if z:
        with zipfile.ZipFile(z[0]) as f:
            f.extractall('/kaggle/working')
    else:
        src = glob.glob('/kaggle/input/**/ai_core/__init__.py', recursive=True)
        if not src:
            raise SystemExit('KHONG thay ai_core trong /kaggle/input')
        sys.path.insert(0, os.path.dirname(os.path.dirname(src[0])))

import torch                                                            # noqa: E402
from torch.utils.data import DataLoader                                 # noqa: E402

from ai_core import build_model                                         # noqa: E402
from ai_core.config import ModelConfig, TrainConfig                     # noqa: E402
from ai_core.training import Trainer                                    # noqa: E402
from ai_core.training.checkpoint import load_checkpoint                 # noqa: E402
from ai_core.training.datasets import HighlightWindowDataset            # noqa: E402
from ai_core.training.datasets.highlight_dataset import normalize_per_video  # noqa: E402
from ai_core.training.loss_fns import LOSS_FNS                          # noqa: E402
from ai_core.scripts.train import _highlight_metric                     # noqa: E402

print('torch', torch.__version__, '| CUDA', torch.cuda.is_available(),
      '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU', flush=True)
if not torch.cuda.is_available():
    raise SystemExit('Khong co GPU — bat Settings > Accelerator > GPU T4 roi chay lai')

f = glob.glob('/kaggle/input/**/highlight_features_140.pt', recursive=True)
if not f:
    raise SystemExit('Thieu highlight_features_140.pt trong /kaggle/input')
raw = torch.load(f[0], map_location='cpu', weights_only=False)
print({k: len(v) for k, v in raw.items()}, flush=True)
if sum(len(v) for v in raw.values()) != 273:
    raise SystemExit('Cho doi 273 hiep — sai dataset')

WIN = 120
VDIM, ADIM = raw['train'][0]['vision'].shape[-1], raw['train'][0]['audio'].shape[-1]
NORMED = {split: [{**s, 'vision': normalize_per_video(s['vision']), 'audio': normalize_per_video(s['audio'])} for s in halves]
          for split, halves in (('train', raw['train']), ('val', raw['val']))}


def run(norm, aug, seed, ckpt_dir, d_model=128, dropout=0.3, steps=4000):
    data = NORMED if norm else raw
    tr = HighlightWindowDataset(data['train'], WIN, WIN // 2, augment=aug)
    va = HighlightWindowDataset(data['val'], WIN, WIN // 2)
    loaders = (DataLoader(tr, batch_size=32, shuffle=True, drop_last=True, num_workers=2, pin_memory=True),
               DataLoader(va, batch_size=32))
    mcfg = ModelConfig(name='highlight_fusion', d_model=d_model, n_heads=8, dropout=dropout,
                       vision_dim=VDIM, audio_dim=ADIM, window_seconds=WIN)
    tcfg = TrainConfig(model='highlight_fusion', lr=3e-4, weight_decay=0.1, batch_size=32,
                       max_steps=steps, warmup_ratio=0.05, precision='bf16', seed=seed,
                       eval_every=100, metric_name='f1', ckpt_dir=ckpt_dir, log_dir='')
    Trainer(build_model('highlight_fusion', mcfg), *loaders, tcfg, loss_fn=LOSS_FNS['highlight_fusion'],
            model_cfg=mcfg, compute_metric=_highlight_metric).train()
    return load_checkpoint(ckpt_dir + '/highlight_fusion/best.pt')['metrics']


summary = {'variants': {}, 'registered': '.claude/evaluation_plan.md §2.1 Vong 6'}
for norm in (0, 1):
    for aug in (0, 1):
        t0, name = time.time(), f'n{norm}_a{aug}'
        m = run(bool(norm), bool(aug), 1337, f'/kaggle/working/r6_{name}_s1337')
        summary['variants'][name] = {'val_f1': m['f1'], 'step': m['step']}
        print(f"{name}: val F1 {m['f1']:.4f} @ step {m['step']} ({(time.time() - t0) / 60:.1f} phut)", flush=True)

best = max(summary['variants'], key=lambda k: summary['variants'][k]['val_f1'])
summary['winner'] = best
print(f'BIEN THE THANG tren val: {best}', flush=True)
shutil.copytree(f'/kaggle/working/r6_{best}_s1337', '/kaggle/working/r6_best_s1337')
norm, aug = bool(int(best[1])), bool(int(best[4]))
for seed in (1338, 1339):
    m = run(norm, aug, seed, f'/kaggle/working/r6_best_s{seed}')
    summary.setdefault('winner_seeds', {})[seed] = {'val_f1': m['f1'], 'step': m['step']}
    print(f"seed {seed}: val F1 {m['f1']:.4f} @ step {m['step']}", flush=True)
json.dump(summary, open('/kaggle/working/r6_summary.json', 'w'), indent=1)
print(json.dumps(summary, indent=1))
print('CHUA CHAM TEST. Cham local theo evaluation_plan §2.1 Vong 6.')
