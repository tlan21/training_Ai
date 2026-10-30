"""Highlight Fusion VONG 8 (AI-20): bong da + tin tuc (nhan nguoi khoatm 2026-10-30).

Kernel MOI (khong dung ai-core-fusion-r7): output vong 7 phai con.
Dang ky truoc: .claude/evaluation_plan.md §2.1 "Vong 8". Cong thuc = vong 7 (chuan hoa + augment, d128/p0.3, lr 3e-4, wd 0.3, 4000 step).
Bien the: lap video tin tuc TRAIN x1, x10, x30; moi bien the 3 seed. Val = val bong da + val tin tuc (3 video).
Chon bien the va quyet dinh lam LOCAL theo quy tac dang ky.
v2: Trainer ghi val_loss + train loss trung binh + lr moi lan eval -> <ckpt>/highlight_fusion/history.json (theo doi overfit).
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
del raw['test']                                   # test never used here
fn = glob.glob('/kaggle/input/**/highlight_news_labeled.pt', recursive=True)
if not fn:
    raise SystemExit('Thieu highlight_news_labeled.pt (dataset highlight-news-v1)')
news = torch.load(fn[0], map_location='cpu', weights_only=False)
print('news', {k: [h['name'] for h in v] for k, v in news.items()}, flush=True)
if len(news['train']) != 7 or len(news['val']) != 3:
    raise SystemExit('Cho doi tin tuc train 7 / val 3 video')
NEWS = {split: [{**s, 'vision': normalize_per_video(s['vision']), 'audio': normalize_per_video(s['audio'])} for s in halves]
        for split, halves in news.items()}


def run(rep, seed, ckpt_dir, lr=3e-4, wd=0.3, steps=4000, d_model=128, dropout=0.3):
    tr = HighlightWindowDataset(NORMED['train'] + NEWS['train'] * rep, WIN, WIN // 2, augment=True)
    va = HighlightWindowDataset(NORMED['val'] + NEWS['val'], WIN, WIN // 2)
    loaders = (DataLoader(tr, batch_size=32, shuffle=True, drop_last=True, num_workers=2, pin_memory=True),
               DataLoader(va, batch_size=32))
    mcfg = ModelConfig(name='highlight_fusion', d_model=d_model, n_heads=8, dropout=dropout,
                       vision_dim=VDIM, audio_dim=ADIM, window_seconds=WIN)
    tcfg = TrainConfig(model='highlight_fusion', lr=lr, weight_decay=wd, batch_size=32,
                       max_steps=steps, warmup_ratio=0.05, precision='bf16', seed=seed,
                       eval_every=100, metric_name='f1', ckpt_dir=ckpt_dir, log_dir='', val_loss=True)
    Trainer(build_model('highlight_fusion', mcfg), *loaders, tcfg, loss_fn=LOSS_FNS['highlight_fusion'],
            model_cfg=mcfg, compute_metric=_highlight_metric).train()
    return load_checkpoint(ckpt_dir + '/highlight_fusion/best.pt')['metrics'], len(tr)


summary = {'variants': {}, 'registered': '.claude/evaluation_plan.md §2.1 Vong 8'}
for rep in (1, 10, 30):
    for seed in (1337, 1338, 1339):
        t0, name = time.time(), f'rep{rep}_s{seed}'
        m, n_windows = run(rep, seed, f'/kaggle/working/r8_{name}')
        summary['variants'][name] = {'val_f1_combined': m['f1'], 'step': m['step'], 'train_windows': n_windows}
        print(f"{name}: combined val F1 {m['f1']:.4f} @ step {m['step']} | train windows {n_windows} "
              f"({(time.time() - t0) / 60:.1f} phut)", flush=True)
json.dump(summary, open('/kaggle/working/r8_summary.json', 'w'), indent=1)
print(json.dumps(summary, indent=1))
print('CHUA CHAM TEST. Chon bien the + quyet dinh local theo evaluation_plan §2.1 Vong 8.')
