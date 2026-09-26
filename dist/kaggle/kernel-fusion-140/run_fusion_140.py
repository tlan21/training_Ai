"""Sweep Highlight Fusion tren 273 hiep (T1.5) — VONG 5.

Kernel RIENG (xem run_fusion_100.py): Kaggle chi giu output ban MOI NHAT moi kernel.

DU LIEU: 140 tran / 273 hiep (vong 4: 100 tran / 195 hiep). Bo 7 hiep hong am thanh tu file goc
(g15, g18, g60h2, g108). Split boc lai o muc TRAN tren 140 tran, seed 1337 — tap test MOI, chua
tung bi xem. Vong 4 da xem tap test cu hai lan, khong dung lai duoc.

Giu NGUYEN luoi config va quy trinh vong 4 de so sanh duoc. Hau xu ly (stride 30, gop seed,
lam muot k) KHONG lam o day — no nam o buoc cham local `eval_highlight`, da khoa truoc trong
evaluation_plan §2.1.

TAP TEST KHONG XUAT HIEN O DAY. Chon config chi bang val; test cham dung MOT lan o local.
"""

import glob
import os
import sys
import time
import zipfile

# ---------------------------------------------------------------- 0. nap ai_core
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
from ai_core.training.loss_fns import LOSS_FNS                          # noqa: E402
from ai_core.scripts.train import _highlight_metric                     # noqa: E402

print('torch', torch.__version__, '| CUDA', torch.cuda.is_available(),
      '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU', flush=True)
if not torch.cuda.is_available():
    # Sweep 8 lan train tren CPU la hang chuc gio, gan nhu chac chan bi cat giua chung.
    raise SystemExit('Khong co GPU — bat Settings > Accelerator > GPU T4 roi chay lai')

# ---------------------------------------------------------------- 1. du lieu
# Chi dinh RO ten file 273 hiep. Cac dataset cu mang ten khac nhau nhung cung dang; neu glob
# ten cu ma lo attach ca hai thi train tren tap nao la do thu tu glob quyet dinh — sai am tham,
# F1 van ra binh thuong, khong co gi bao.
f = glob.glob('/kaggle/input/**/highlight_features_140.pt', recursive=True)
if not f:
    raise SystemExit('Thieu highlight_features_140.pt trong /kaggle/input')
raw = torch.load(f[0], map_location='cpu', weights_only=False)
print({k: len(v) for k, v in raw.items()}, flush=True)

N_EXPECT = 273
if sum(len(v) for v in raw.values()) != N_EXPECT:
    raise SystemExit(f'Cho doi {N_EXPECT} hiep, nhan {sum(len(v) for v in raw.values())} — sai dataset')

WIN = 120
VDIM, ADIM = raw['train'][0]['vision'].shape[-1], raw['train'][0]['audio'].shape[-1]
tr = HighlightWindowDataset(raw['train'], WIN, WIN // 2)
va = HighlightWindowDataset(raw['val'], WIN, WIN // 2)
print(f'cua so train {len(tr)} | val {len(va)} | vision {VDIM}d audio {ADIM}d', flush=True)
if len(va) == 0:
    # Trainer._evaluate tra None khi loader rong -> early-stop im lang vo hieu (da can o T1.3c).
    raise SystemExit('val rong -> early-stop se im lang vo hieu')

loaders = (DataLoader(tr, batch_size=32, shuffle=True, drop_last=True, num_workers=2, pin_memory=True),
           DataLoader(va, batch_size=32))


def run(d_model, dropout, seed, steps, ckpt_dir):
    # Kien truc HARDCODE 2 self + 2 cross theo model_spec §2 nen n_layers bi bo qua; num chinh con
    # lai la d_model + dropout.
    mcfg = ModelConfig(name='highlight_fusion', d_model=d_model, n_heads=8, dropout=dropout,
                       vision_dim=VDIM, audio_dim=ADIM, window_seconds=WIN)
    tcfg = TrainConfig(model='highlight_fusion', lr=3e-4, weight_decay=0.1, batch_size=32,
                       max_steps=steps, warmup_ratio=0.05, precision='bf16', seed=seed,
                       eval_every=100, metric_name='f1', ckpt_dir=ckpt_dir, log_dir='')
    model = build_model('highlight_fusion', mcfg)
    Trainer(model, *loaders, tcfg, loss_fn=LOSS_FNS['highlight_fusion'],
            model_cfg=mcfg, compute_metric=_highlight_metric).train()
    return load_checkpoint(ckpt_dir + '/highlight_fusion/best.pt')['metrics']


# ---------------------------------------------------------------- 2. sweep tren VAL
CONFIGS = [(64, 0.1), (128, 0.1), (128, 0.3), (256, 0.1), (256, 0.3)]
scores = {}
for d_model, dropout in CONFIGS:
    t0 = time.time()
    m = run(d_model, dropout, 1337, 4000, f'/kaggle/working/sweep_d{d_model}_p{int(dropout * 10)}')
    scores[(d_model, dropout)] = m['f1']
    print(f"d={d_model:3} dropout={dropout}: val F1 {m['f1']:.4f} @ step {m['step']:4} "
          f"({(time.time() - t0) / 60:.1f} phut)", flush=True)

best = max(scores, key=scores.get)
print()
print(f'CONFIG THANG tren val: d_model={best[0]} dropout={best[1]} (F1 {scores[best]:.4f})', flush=True)

# ---------------------------------------------------------------- 3. 3 seed cho config thang
seed_f1 = {}
for seed in (1337, 1338, 1339):
    m = run(*best, seed, 4000, f'/kaggle/working/ckpt_fusion_best_s{seed}')
    seed_f1[seed] = m['f1']
    print(f"seed {seed}: val F1 {m['f1']:.4f} @ step {m['step']}", flush=True)

vals = torch.tensor(list(seed_f1.values()))
print()
print(f'val F1 qua 3 seed: {vals.mean():.4f} +/- {vals.std():.4f}')
print('VONG 4 de so sanh (tap val CU, 20 hiep, chua hau xu ly): 3 seed 0.2124-0.2274')
print('CHUA CHAM TEST. Cham o local bang ai_core.scripts.eval_highlight, dung mot lan.')
