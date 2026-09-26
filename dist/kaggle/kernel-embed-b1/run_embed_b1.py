"""Trich embedding 1fps cho 40 hiep MOI cua lo 1 (g80..g99) — T1.5a, chi buoc embedding.

Day la KERNEL RIENG, khong phai them mot cell vao kaggle_train.ipynb. Hai ly do:
  1. Kaggle chi giu output cua ban MOI NHAT cua moi kernel. Dung chung kernel voi ai-core-train
     nghia la lan train fusion ke tiep se xoa mat file embedding nay. Da mat ckpt Siamese cua v22
     dung kieu do, khong co duong nao lay lai.
  2. Run A trong notebook do gop shot-groups + TRAIN Siamese + embedding vao mot khoi, khong tach
     duoc. Train lai Siamese se ra trong so khac, va embedding cua 40 hiep moi lech phan phoi so
     voi 160 hiep cu — shape van (n, 256), fusion van train duoc, khong co gi bao, chi F1 tut.

Vi vay kernel nay NAP LAI dung checkpoint da sinh ra soccernet_vision_80.pt (siamese_best.pt,
md5 9d2f670f3ab985844478b006300058d5) va khong train gi ca.

Output: /kaggle/working/soccernet_vision_b1.pt = {stem: Tensor(n_sec, 256)} cho dung 40 hiep.
Tai ve roi gop voi soccernet_vision_80.pt (160 hiep) thanh ban 200 hiep.
"""

import glob
import json
import os
import shutil
import sys
import time
import zipfile

N_HALVES = 40
JPG_DIR = 'frames_jpg_b1'
LOCAL = f'/tmp/frames_b1/{JPG_DIR}'      # KHONG /kaggle/working: do la thu muc OUTPUT, copy anh
                                         # vao la `kernels output` sau nay tai lai ca 1,7 GB anh.

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

import torch                                                    # noqa: E402
from ai_core.scripts import extract_vit_embeddings              # noqa: E402

print('torch', torch.__version__, '| CUDA', torch.cuda.is_available(),
      '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU', flush=True)
if not torch.cuda.is_available():
    # 108k frame la ~15 phut GPU so voi ~5 gio CPU. Chay CPU gan nhu chac chan bi cat giua chung,
    # ma extract_vit_embeddings chi luu sau tung hiep nen se ra file thieu hiep.
    raise SystemExit('Khong co GPU — bat Settings > Accelerator > GPU T4 roi chay lai')

# ---------------------------------------------------------------- 1. tim anh, copy sang dia local
# Neo vao mot file .jpg THAT roi lui hai cap, khong tim theo TEN thu muc: Kaggle giai nen zip vao
# mot folder trung ten nen duong dan thanh 'frames_jpg_b1/frames_jpg_b1/g80h1/...', glob theo ten
# tra ve ca hai tang va sorted() khong bao dam tang nao truoc (bay nay da can that o Run A).
sample = glob.glob(f'/kaggle/input/**/{JPG_DIR}/*/*.jpg', recursive=True)
if not sample:
    raise SystemExit(f'Khong thay {JPG_DIR}/*/*.jpg trong /kaggle/input')
FRAMES_ROOT = os.path.dirname(os.path.dirname(sample[0]))
print('frames root:', FRAMES_ROOT, f'({len(os.listdir(FRAMES_ROOT))} hiep)', flush=True)

# /kaggle/input la filesystem MANG — doc 108k JPEG le tu do cham hon nhieu lan so voi copy mot lan.
if not os.path.isdir(LOCAL):
    t = time.time()
    shutil.copytree(FRAMES_ROOT, LOCAL)
    print(f'copy -> dia local trong {(time.time() - t) / 60:.1f} phut', flush=True)

# ---------------------------------------------------------------- 2. manifest: dung lai duong dan
man_path = glob.glob(f'/kaggle/input/**/{JPG_DIR}.json', recursive=True)
if not man_path:
    raise SystemExit(f'Thieu {JPG_DIR}.json trong /kaggle/input')
with open(man_path[0], encoding='utf-8') as f:
    man = json.load(f)
for it in man['items']:
    g, sec = it['group'], it['extra']['sec']
    it['path'] = f'{LOCAL}/{g}/{g}_s{sec:05d}.jpg'      # dung lai tu group+sec, KHONG parse path
    it['extra'].pop('src', None)                        # Windows ('D:/...\\g80h1\\...') trong manifest
MANIFEST = '/tmp/frames_b1.json'
with open(MANIFEST, 'w', encoding='utf-8') as f:
    json.dump(man, f, ensure_ascii=False)

missing = [i['path'] for i in man['items'][:300] if not os.path.exists(i['path'])]
if missing:
    raise SystemExit(f'{len(missing)}/300 file mau khong ton tai, vd {missing[0]} — sai layout')
groups = sorted({i['group'] for i in man['items']})
if len(groups) != N_HALVES:
    raise SystemExit(f'Manifest co {len(groups)} hiep, cho doi {N_HALVES} — sai dataset')
print(f"{len(man['items']):,} frame | {len(groups)} hiep ({groups[0]}..{groups[-1]})", flush=True)

# ---------------------------------------------------------------- 3. embedding
ck = glob.glob('/kaggle/input/**/siamese_best.pt', recursive=True)
if not ck:
    raise SystemExit('Thieu siamese_best.pt trong /kaggle/input')

OUT = '/kaggle/working/soccernet_vision_b1.pt'
sys.argv = ['extract_vit_embeddings', '--checkpoint', ck[0], '--manifest', MANIFEST,
            '--out', OUT, '--batch-size', '256']
t = time.time()
extract_vit_embeddings.main()

emb = torch.load(OUT, map_location='cpu', weights_only=False)
print(f'embedding {len(emb)} hiep trong {(time.time() - t) / 60:.0f} phut | '
      f'{os.path.getsize(OUT) / 1e6:.0f} MB', flush=True)
# Thieu hiep phai NO o day. extract_vit_embeddings luu sau tung hiep, nen kernel bi cat giua chung
# van de lai mot file .pt doc duoc — gop vao ban 200 hiep thi cac hiep thieu bi bo im lang.
short = {g: tuple(emb[g].shape) for g in emb if emb[g].shape[0] < 1000}
if len(emb) != N_HALVES or short:
    raise SystemExit(f'Chua xong: {len(emb)}/{N_HALVES} hiep, hiep ngan: {short}')
print('DU 40 HIEP — tai /kaggle/working/soccernet_vision_b1.pt ve')
