"""AI-05 ablation A3 (registered in coordination/claude/TASKS.md BEFORE features were extracted or anything ran):
Highlight Fusion image tokens — frozen Siamese backbone (control, `vision` already in highlight_features_140.pt) vs frozen
ViT-classifier backbone (variant, 256-d, active checkpoint 192d90e4, extracted locally by a3_extract.py from the same 1 fps
JPGs; alignment check passed). Only difference: the per-second image vector. Audio, labels, split, seconds per half unchanged.

Order:
  0. load ai_core, GPU check
  1. data: control file + one ViT file per half; same 273 names/shapes, labels/audio untouched -> else stop
  2. SANITY (any FAIL = stop): gradient check, AdamW parity, fusion model test, overfit 1 real batch (4 windows x 120 s,
     d256, dropout 0, 300 steps, warmup 100 -> lr 1e-3) for BOTH branches, masked BCE < 0.05
  3. 2 branches x seeds 1337/1338/1339, recipe of T1.5e / kernel-fusion-140 run(): d256, 8 heads, dropout 0.3, 4000 steps,
     lr 3e-4, wd 0.1, warmup 5%, bf16, batch 32, windows 120 s stride 60, best.pt by val F1 (Trainer, eval every 100)
  4. per seed: per-second scores on whole halves (eval_highlight.model_scores, no overlap, no smoothing), tau swept on VAL,
     then TEST scored exactly once at that tau: F1/second + AP (pooled, mean per half). -> /kaggle/working/a3_eval.json
     (rewritten after every run). Mean +- std and Welch t are computed locally from that file.
Output: a3_eval.json, ckpt_{branch}_s{seed}/highlight_fusion/best.pt. DOWNLOAD before pushing another version.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

BRANCHES = ['siamese', 'vit']
SEEDS = [1337, 1338, 1339]
WIN, D_MODEL, DROPOUT, STEPS = 120, 256, 0.3, 4000
OUT = '/kaggle/working'

# ---------------------------------------------------------------- 0. ai_core
CODE = '/tmp/code'
if not os.path.isdir(f'{CODE}/ai_core'):
    z = glob.glob('/kaggle/input/**/ai_core.zip', recursive=True)
    pkg = [os.path.dirname(p) for p in glob.glob('/kaggle/input/**/ai_core/__init__.py', recursive=True)
           if os.path.isdir(os.path.join(os.path.dirname(p), 'training'))]
    if z:
        with zipfile.ZipFile(z[0]) as f:
            f.extractall(CODE)
    elif pkg:
        shutil.copytree(pkg[0], f'{CODE}/ai_core')
    else:
        raise SystemExit('KHONG thay ai_core (zip hoac thu muc) trong /kaggle/input')
sys.path.insert(0, CODE)

import torch                                                            # noqa: E402
from torch.utils.data import DataLoader                                 # noqa: E402

if not torch.cuda.is_available():
    raise SystemExit('Khong co GPU — bat Accelerator GPU T4 roi chay lai')
print('torch', torch.__version__, '|', torch.cuda.get_device_name(0), flush=True)

from ai_core import build_model                                         # noqa: E402
from ai_core.config import ModelConfig, TrainConfig                     # noqa: E402
from ai_core.optim import AdamW, split_decay_params                     # noqa: E402
from ai_core.scripts.eval_highlight import model_scores, sweep_tau     # noqa: E402
from ai_core.scripts.evaluate import f1_per_second                      # noqa: E402
from ai_core.scripts.train import _highlight_metric                     # noqa: E402
from ai_core.training import Trainer                                    # noqa: E402
from ai_core.training.checkpoint import load_checkpoint                 # noqa: E402
from ai_core.training.datasets import HighlightWindowDataset            # noqa: E402
from ai_core.training.loss_fns import LOSS_FNS                          # noqa: E402
from ai_core.training.trainer import set_seed                           # noqa: E402

# ---------------------------------------------------------------- 1. data
f = glob.glob('/kaggle/input/**/highlight_features_140.pt', recursive=True)
if len(f) != 1:
    raise SystemExit(f'can dung 1 highlight_features_140.pt, thay {len(f)}')
control = torch.load(f[0], map_location='cpu', weights_only=False)
vit_files = {os.path.basename(p)[:-3]: p for p in glob.glob('/kaggle/input/**/g*h[12].pt', recursive=True)}
names = [h['name'] for s in ('train', 'val', 'test') for h in control[s]]
if len(names) != 273 or set(names) != set(vit_files):
    raise SystemExit(f'halves: control {len(names)}, vit files {len(vit_files)}, missing {sorted(set(names) - set(vit_files))[:5]}')
variant, cos = {}, []
for s in ('train', 'val', 'test'):
    variant[s] = []
    for h in control[s]:
        v = torch.load(vit_files[h['name']], map_location='cpu')
        if v.shape != h['vision'].shape:
            raise SystemExit(f"{h['name']}: vit {tuple(v.shape)} != control {tuple(h['vision'].shape)}")
        variant[s].append({'name': h['name'], 'vision': v, 'audio': h['audio'], 'labels': h['labels']})
        cos.append(float(torch.nn.functional.cosine_similarity(v, h['vision']).mean()))
DATA = {'siamese': control, 'vit': variant}
print(f"DATA OK: {[len(control[s]) for s in ('train', 'val', 'test')]} halves | seconds "
      f"{sum(h['labels'].shape[0] for s in control.values() for h in s):,} | mean cosine vit vs siamese per half "
      f"{sum(cos) / len(cos):.3f} (different backbones expected)", flush=True)
VDIM, ADIM = control['train'][0]['vision'].shape[-1], control['train'][0]['audio'].shape[-1]


def loaders(branch):
    tr = HighlightWindowDataset(DATA[branch]['train'], WIN, WIN // 2)
    va = HighlightWindowDataset(DATA[branch]['val'], WIN, WIN // 2)
    if len(va) == 0:
        raise SystemExit('val rong -> early-stop vo hieu')
    return (DataLoader(tr, batch_size=32, shuffle=True, drop_last=True, num_workers=2, pin_memory=True),
            DataLoader(va, batch_size=32))


def make(seed, dropout):
    set_seed(seed)
    mcfg = ModelConfig(name='highlight_fusion', d_model=D_MODEL, n_heads=8, dropout=dropout,
                       vision_dim=VDIM, audio_dim=ADIM, window_seconds=WIN)
    return build_model('highlight_fusion', mcfg), mcfg


# ---------------------------------------------------------------- 2. sanity
os.chdir(CODE)
lines = []
for name, target in (('gradient check < 1e-4', 'ai_core/tests/test_gradient_check.py'),
                     ('AdamW parity < 1e-6', 'ai_core/tests/test_adamw_parity.py'),
                     ('highlight fusion shape + overfit', 'ai_core/tests/test_models.py::test_highlight_fusion_shape_and_overfit')):
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', target], capture_output=True, text=True)
    lines.append(f"SANITY {name}: {'PASS' if r.returncode == 0 else 'FAIL'} | {r.stdout.strip().splitlines()[-1]}")
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-2000:])
for branch in BRANCHES:
    ds = HighlightWindowDataset(DATA[branch]['train'], WIN, WIN // 2)
    g = torch.Generator().manual_seed(0)
    batch = [torch.stack(t).cuda() for t in zip(*[ds[int(i)] for i in torch.randint(len(ds), (4,), generator=g)])]
    model, _ = make(0, 0.0)
    model.cuda().train()
    opt = AdamW(split_decay_params(model), lr=1e-3, weight_decay=0.0)
    for step in range(300):
        for grp in opt.param_groups:
            grp['lr'] = 1e-3 * min(1.0, (step + 1) / 100)
        opt.zero_grad()
        loss = LOSS_FNS['highlight_fusion'](model, batch)
        loss.backward()
        opt.step()
    lines.append(f"SANITY overfit 1 batch that ({branch}, 4 x {WIN} s, 300 buoc): {'PASS' if loss.item() < 0.05 else 'FAIL'} | loss {loss.item():.4f}")
    del model, opt
torch.cuda.empty_cache()
print('\n'.join(lines), flush=True)
if any('FAIL' in s for s in lines):
    raise SystemExit('Sanity FAIL — khong train')


# ---------------------------------------------------------------- 3/4. train + score
def average_precision(score, label):
    keep = label != -1
    score, label = score[keep], label[keep].float()
    hits = label[torch.argsort(-score, stable=True)]
    precision = hits.cumsum(0) / torch.arange(1, len(hits) + 1)
    return float((precision * hits).sum() / hits.sum().clamp(min=1))


result = {'recipe': {'d_model': D_MODEL, 'dropout': DROPOUT, 'steps': STEPS, 'window': WIN, 'lr': 3e-4, 'wd': 0.1,
                     'warmup_ratio': 0.05, 'batch': 32}, 'sanity': lines, 'runs': {}}
for branch in BRANCHES:
    tr_loader, va_loader = loaders(branch)
    for seed in SEEDS:
        t0 = time.time()
        ckpt_dir = f'{OUT}/ckpt_{branch}_s{seed}'
        model, mcfg = make(seed, DROPOUT)
        tcfg = TrainConfig(model='highlight_fusion', lr=3e-4, weight_decay=0.1, batch_size=32, max_steps=STEPS,
                           warmup_ratio=0.05, precision='bf16', seed=seed, eval_every=100, metric_name='f1',
                           ckpt_dir=ckpt_dir, log_dir='')
        Trainer(model, tr_loader, va_loader, tcfg, loss_fn=LOSS_FNS['highlight_fusion'], model_cfg=mcfg,
                compute_metric=_highlight_metric).train()
        ckpt = load_checkpoint(f'{ckpt_dir}/highlight_fusion/best.pt', map_location='cpu')
        best, _ = make(seed, DROPOUT)
        best.load_state_dict(ckpt['state_dict'])
        best.eval()
        per = {s: [model_scores(best, h, WIN) for h in DATA[branch][s]] for s in ('val', 'test')}
        lab = {s: [h['labels'] for h in DATA[branch][s]] for s in ('val', 'test')}
        tau, val_f1 = sweep_tau(torch.cat(per['val']), torch.cat(lab['val']))
        test_score, test_lab = torch.cat(per['test']), torch.cat(lab['test'])   # TEST: scored once, tau from val
        run = {'branch': branch, 'seed': seed, 'params': sum(p.numel() for p in best.parameters()),
               'best_step': ckpt['metrics'].get('step'), 'val_f1_at_0.5': ckpt['metrics'].get('f1'),
               'tau': tau, 'val_f1': val_f1, 'test_f1': f1_per_second(test_score, test_lab, thresh=tau),
               'test_ap_pooled': average_precision(test_score, test_lab),
               'test_ap_mean_per_half': sum(average_precision(s, y) for s, y in zip(per['test'], lab['test']) if (y == 1).any())
                                        / sum(1 for y in lab['test'] if (y == 1).any()),
               'minutes': round((time.time() - t0) / 60, 1)}
        result['runs'][f'{branch}_s{seed}'] = run
        json.dump(result, open(f'{OUT}/a3_eval.json', 'w'), indent=1)
        print(f"RESULT {branch} s{seed}: best step {run['best_step']} | tau {tau:.2f} val F1 {val_f1:.4f} -> "
              f"TEST F1 {run['test_f1']:.4f} AP {run['test_ap_pooled']:.4f} (per half {run['test_ap_mean_per_half']:.4f}) "
              f"| params {run['params']:,} | {run['minutes']} min", flush=True)
print('A3 DONE', flush=True)
