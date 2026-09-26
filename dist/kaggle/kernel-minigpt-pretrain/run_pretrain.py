"""Pretrain Mini-GPT next-token tren Wikipedia tieng Viet (T1.6b).

Kernel RIENG: Kaggle chi giu output ban MOI NHAT moi kernel, dung chung kernel khac la mat ckpt.

Model dung model_spec: d384, 6 layer, 6 head, ctx 1024, BPE 8192 tied (~14M tham so). Batch hieu
dung 8 x accum 8 = 64 chunk = 65.536 token/step, lr 6e-4 cosine, wd 0.1.

max_steps KHONG dat cung: do toc do that (15 step + 1 lan cham perplexity) roi tinh sao cho vua
BUDGET_H gio. Dat cung thi hoac thua (bo phi quota) hoac vuot 12h Kaggle -> kernel bi giet, mat het
output. Lich LR cosine phu thuoc max_steps nen phai biet truoc khi train that.

Precision: bf16 neu GPU co bf16 PHAN CUNG (A100/L4), nguoc lai fp16 + GradScaler (T4). bf16 tren
T4 la gia lap, cham hon nhieu lan.
"""

import glob
import os
import shutil
import sys
import time
import zipfile

BUDGET_H = 9.0
EVAL_EVERY = 250

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

print('torch', torch.__version__, '| CUDA', torch.cuda.is_available(),
      '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU', flush=True)
if not torch.cuda.is_available():
    raise SystemExit('Khong co GPU — bat Settings > Accelerator > GPU T4 roi chay lai')
PREC = 'bf16' if torch.cuda.is_bf16_supported(including_emulation=False) else 'fp16'
print('precision:', PREC, flush=True)

# ---------------------------------------------------------------- 1. du lieu
tb = glob.glob('/kaggle/input/**/train.bin', recursive=True)
vb = glob.glob('/kaggle/input/**/bpe_vocab.json', recursive=True)
if len(tb) != 1 or len(vb) != 1:
    raise SystemExit(f'can dung 1 train.bin va 1 bpe_vocab.json, thay {len(tb)} / {len(vb)}')
TOK = '/tmp/tokens'                     # copy ra dia local: /kaggle/input la o mang, memmap doc ngau nhien cham
if not os.path.isdir(TOK):
    shutil.copytree(os.path.dirname(tb[0]), TOK)
print({f: f'{os.path.getsize(os.path.join(TOK, f)) / 1e6:.0f} MB' for f in sorted(os.listdir(TOK))}, flush=True)

from ai_core.scripts import train as train_script                       # noqa: E402

CFG = '/tmp/minigpt_pretrain.yaml'


def write_cfg(max_steps, eval_every, ckpt_dir):
    open(CFG, 'w').write(f"""model:
  name: minigpt
  d_model: 384
  n_layers: 6
  n_heads: 6
  vocab_size: 8192
  context_len: 1024
train:
  model: minigpt
  lr: 6.0e-4
  weight_decay: 0.1
  batch_size: 8
  grad_accum: 8
  max_steps: {max_steps}
  warmup_ratio: 0.03
  min_lr_ratio: 0.10
  precision: {PREC}
  seed: 1337
  metric_name: perplexity
  eval_every: {eval_every}
  ckpt_dir: {ckpt_dir}
  log_dir: ''
""")


def run(val_batches=100):
    sys.argv = ['train', '--config', CFG, '--vocab', vb[0], '--tokens', TOK,
                '--val-batches', str(val_batches)]
    train_script.main()


# ---------------------------------------------------------------- 2. do toc do that
write_cfg(15, 15, '/tmp/bench')                       # 15 step + dung 1 lan eval o step 15
t = time.time()
run()
bench = time.time() - t
# bench gom 15 step + 1 eval + khoi dong, nen s/step bi uoc CAO — an toan cho han 12h.
sec_step = bench / 15
steps = int(BUDGET_H * 3600 / (sec_step * (1 + 1.0 / EVAL_EVERY)))
print(f'BENCH: {bench:.0f}s cho 15 step -> {sec_step:.2f} s/step -> max_steps {steps} '
      f'(~{steps * 65536 / 1e9:.2f}B token, {BUDGET_H}h)', flush=True)
shutil.rmtree('/tmp/bench', ignore_errors=True)

# ---------------------------------------------------------------- 3. train that
write_cfg(steps, EVAL_EVERY, '/kaggle/working/ckpt_minigpt')
run()
print('XONG — tai /kaggle/working/ckpt_minigpt/minigpt/best.pt ve', flush=True)
