"""T1.3a/b — train ViT phan loai 4 lop (bong_da, the_thao, ca_nhac, tin_tuc) 3 seed + cham test.

KERNEL RIENG (khong dung chung ai-core-train): Kaggle chi giu output cua ban MOI NHAT moi kernel,
dung chung la lan train sau xoa mat checkpoint (da mat ckpt Siamese v22 dung kieu do).

Thu tu:
  0. nap ai_core, chon precision (T4 khong co bf16 phan cung -> fp16 + GradScaler)
  1. copy JPEG ra dia local, dung lai manifest voi duong dan local, kiem so luong
  2. SANITY (skill ai_training_task buoc 3): gradient check, AdamW parity, overfit ViT nho,
     overfit 1 batch THAT voi config that -> in 4 dong; hong cai nao la dung, khong train
  3. do toc do -> uoc tong thoi gian 3 seed; qua ngan sach thi DUNG, khong tu cat max_steps
     (max_steps la hyperparameter cua vit.yaml, khong phai num do theo quota)
  4. train 3 seed, checkpoint best theo accuracy val
  5. eval_vit: Top-1 mean+-std + macro-F1 + confusion + 2 baseline tren cung test

Output: /kaggle/working/vit_s{seed}/vit/{best,last}.pt, vit_eval.json. TAI VE TRUOC khi push ban sau.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

SEEDS = [1337, 1338, 1339]
EVAL_EVERY = 1000              # val 6k frame ~15s; eval moi 100 step (mac dinh train.py) = ~50 phut/seed
WORKERS = 4                    # Kaggle 4 vCPU; giai ma JPEG + augment la nut co chai, khong phai GPU
BUDGET_H = 10.0                # han kernel 12h, chua 2h cho sanity + eval
LOCAL = '/tmp/vit_4cls_jpg'    # KHONG /kaggle/working: do la thu muc OUTPUT, copy anh vao la tai ve ca 2 GB
EXPECT = {'items': 63784, 'groups': 123,
          'classes': ['bong_da', 'ca_nhac', 'the_thao', 'tin_tuc']}

# ---------------------------------------------------------------- 0. nap ai_core
# Kaggle TU GIAI NEN ai_core.zip cua dataset code -> trong /kaggle/input chi con thu muc ai_core/
# (v1 kernel nay chet o day vi chi tim .zip). Nhan ca hai dang, dua ve /tmp/code (khong vao
# /kaggle/working de khong lan vao output).
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
import yaml                                                             # noqa: E402

print('torch', torch.__version__, '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
      flush=True)
if not torch.cuda.is_available():
    raise SystemExit('Khong co GPU — bat Accelerator GPU T4 roi chay lai')
PREC = 'bf16' if torch.cuda.is_bf16_supported(including_emulation=False) else 'fp16'
print('precision:', PREC, flush=True)

# ---------------------------------------------------------------- 1. du lieu
# Neo vao mot file .jpg THAT roi lui hai cap: Kaggle giai nen zip vao folder trung ten nen duong dan
# co the la vit_4cls_jpg/vit_4cls_jpg/<group>/..., glob theo ten thu muc tra ve ca hai tang.
sample = glob.glob('/kaggle/input/**/vit_4cls_jpg/*/*.jpg', recursive=True)
if not sample:
    raise SystemExit('Khong thay vit_4cls_jpg/*/*.jpg trong /kaggle/input')
root = os.path.dirname(os.path.dirname(sample[0]))
if not os.path.isdir(LOCAL):
    t = time.time()
    shutil.copytree(root, LOCAL)      # /kaggle/input la o mang: doc 64k JPEG le tu do cham hon nhieu
    print(f'copy {root} -> {LOCAL} trong {(time.time() - t) / 60:.1f} phut', flush=True)

man_path = glob.glob('/kaggle/input/**/vit_4cls_jpg.json', recursive=True)
if not man_path:
    raise SystemExit('Thieu vit_4cls_jpg.json trong /kaggle/input')
man = json.load(open(man_path[0], encoding='utf-8'))
for it in man['items']:
    it['path'] = f"{LOCAL}/{it['path']}"
MANIFEST = '/tmp/vit_4cls.json'
json.dump(man, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False)

missing = [i['path'] for i in man['items'] if not os.path.exists(i['path'])]
groups = {i['group'] for i in man['items']}
classes = sorted({i['label'] for i in man['items']})
split_of = {}
for i in man['items']:
    split_of.setdefault(i['group'], set()).add(i['split'])
if missing or len(man['items']) != EXPECT['items'] or len(groups) != EXPECT['groups'] \
        or classes != EXPECT['classes'] or any(len(s) != 1 for s in split_of.values()):
    raise SystemExit(f"Du lieu sai: thieu {len(missing)} file, {len(man['items'])} item, "
                     f"{len(groups)} video, lop {classes}")
cnt = {c: sum(i['label'] == c for i in man['items']) for c in classes}
print(f"DATA OK: {len(man['items']):,} frame | {len(groups)} video | {cnt}", flush=True)

# ---------------------------------------------------------------- 2. sanity
os.chdir(CODE)                       # pytest import ai_core tu cwd
lines = []
for name, target in (('gradient check < 1e-4', 'ai_core/tests/test_gradient_check.py'),
                     ('AdamW parity < 1e-6', 'ai_core/tests/test_adamw_parity.py'),
                     ('overfit ViT nho (synthetic)', 'ai_core/tests/test_models.py::test_vit_shape_and_overfit')):
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', target],
                       capture_output=True, text=True)
    lines.append(f"SANITY {name}: {'PASS' if r.returncode == 0 else 'FAIL'} | {r.stdout.strip().splitlines()[-1]}")
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-2000:])

from ai_core import build_model                                          # noqa: E402
from ai_core.config import load_configs                                  # noqa: E402
from ai_core.optim import AdamW, split_decay_params                      # noqa: E402
from ai_core.training.datasets import ViTKeyframeDataset                 # noqa: E402

VIT_YAML = f'{CODE}/ai_core/training/configs/vit.yaml'
model_cfg, _ = load_configs(VIT_YAML)
torch.manual_seed(0)
ds = ViTKeyframeDataset(MANIFEST, 'train', model_cfg.img_size)
idx = torch.randperm(len(ds))[:32].tolist()
x = torch.stack([ds[i][0] for i in idx]).cuda()
y = torch.stack([ds[i][1] for i in idx]).cuda()
model = build_model('vit', model_cfg).cuda()
opt = AdamW(split_decay_params(model), lr=1e-3, weight_decay=0.0)
for _ in range(300):
    opt.zero_grad()
    loss = torch.nn.functional.cross_entropy(model(x), y)
    loss.backward()
    opt.step()
ok = loss.item() < 0.05
lines.append(f"SANITY overfit 1 batch that (config vit.yaml, 32 anh, 300 buoc): "
             f"{'PASS' if ok else 'FAIL'} | loss {loss.item():.4f}")
del model, opt, x, y
torch.cuda.empty_cache()
print('\n'.join(lines), flush=True)
if any('FAIL' in s for s in lines):
    raise SystemExit('Sanity FAIL — khong train')

# ---------------------------------------------------------------- 3. do toc do
from ai_core.scripts import train as train_script                       # noqa: E402

with open(VIT_YAML, encoding='utf-8') as f:
    base = yaml.safe_load(f)
MAX_STEPS = base['train']['max_steps']


def run(seed, max_steps, eval_every, ckpt_dir):
    cfg = json.loads(json.dumps(base))
    cfg['train'].update(seed=seed, max_steps=max_steps, eval_every=eval_every, precision=PREC,
                        ckpt_dir=ckpt_dir, log_dir='')
    path = f'/tmp/vit_s{seed}.yaml'
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(cfg, f)
    sys.argv = ['train', '--config', path, '--manifest', MANIFEST, '--workers', str(WORKERS)]
    train_script.main()


# v2 bench 40 step: khoi dong worker + 1 lan eval (11s) chiem gan het -> 0.64 s/step, trong khi toc
# do on dinh la ~0.33 s/step; uoc 10.6h thay vi ~6h va kernel tu dung oan. 300 step van gom khoi
# dong + eval nen van uoc CAO (an toan cho han 12h), chi khong con vo ly.
BENCH_STEPS = 300
t = time.time()
run(0, BENCH_STEPS, BENCH_STEPS, '/tmp/bench')
sec_step = (time.time() - t) / BENCH_STEPS
shutil.rmtree('/tmp/bench', ignore_errors=True)
need_h = sec_step * MAX_STEPS * len(SEEDS) / 3600
print(f'BENCH {sec_step:.3f} s/step -> {len(SEEDS)} seed x {MAX_STEPS} step ~ {need_h:.1f} h', flush=True)
if need_h > BUDGET_H:
    raise SystemExit(f'Uoc {need_h:.1f} h > ngan sach {BUDGET_H} h — tach seed ra nhieu lan chay, '
                     'khong cat max_steps')

# ---------------------------------------------------------------- 4. train 3 seed
ckpts = []
for seed in SEEDS:
    t = time.time()
    run(seed, MAX_STEPS, EVAL_EVERY, f'/kaggle/working/vit_s{seed}')
    ckpts.append(f'/kaggle/working/vit_s{seed}/vit/best.pt')
    print(f'seed {seed} xong trong {(time.time() - t) / 3600:.2f} h', flush=True)

# ---------------------------------------------------------------- 5. cham test
from ai_core.scripts import eval_vit                                     # noqa: E402

sys.argv = ['eval_vit', '--manifest', MANIFEST, '--checkpoint', *ckpts,
            '--out', '/kaggle/working/vit_eval.json', '--workers', str(WORKERS)]
eval_vit.main()
print('\n'.join(lines))
print('XONG — tai /kaggle/working/vit_s*/vit/best.pt + vit_eval.json ve TRUOC khi push ban sau', flush=True)
