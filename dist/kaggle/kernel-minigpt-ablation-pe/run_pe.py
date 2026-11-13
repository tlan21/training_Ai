"""AI-05 ablation A2 (evaluation_plan §2.2, registered in coordination/claude/TASKS.md BEFORE this kernel ran):
MiniGPT small (d256, 4 layers, 4 heads, vocab 8192) — RoPE (project) vs learned positional embedding (GPT-2 table 1024 x d).
Only difference: ModelConfig.pos_encoding. Data viwiki-tokens-8192 unchanged. Train windows 256 tokens, 65,536 tokens/step
(batch 32 x accum 8, = minigpt_pretrain 8 x 8 x 1024), lr 6e-4, wd 0.1, warmup 3%, cosine to 0.1, grad clip 1.0, fp16 on T4.

Order:
  0. load ai_core, GPU check
  1. copy tokens to local disk, check vocab 8192
  2. SANITY: gradient check, AdamW parity, pos_encoding tests, overfit 1 real batch for BOTH variants -> any FAIL = stop
  3. bench both variants -> N steps = largest (multiple of 500, <= 20000) fitting 6 runs in the 10 h budget; printed BEFORE training
  4. 2 variants x seeds 1337/1338/1339, N steps each; the FINAL checkpoint is evaluated (no selection on val)
  5. val perplexity on the first 262,144 val tokens at ctx 256 / 512 / 1024 -> /kaggle/working/pe_eval.json (written after every run)
Output also: /kaggle/working/pe_{variant}_s{seed}.pt (state_dict + config). DOWNLOAD before pushing another version.
"""

import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time
import zipfile

VARIANTS = ['rope', 'learned']
SEEDS = [1337, 1338, 1339]
CTX, EVAL_CTX, EVAL_TOKENS = 256, (256, 512, 1024), 262_144
BATCH, ACCUM, LR, WD, WARM, MIN_RATIO, CLIP = 32, 8, 6e-4, 0.1, 0.03, 0.10, 1.0
BUDGET_H, MAX_N = 10.0, 20_000
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

if not torch.cuda.is_available():
    raise SystemExit('Khong co GPU — bat Accelerator GPU T4 roi chay lai')
print('torch', torch.__version__, '|', torch.cuda.get_device_name(0), flush=True)

from ai_core.config import ModelConfig                                  # noqa: E402
from ai_core.models.minigpt import MiniGPT                              # noqa: E402
from ai_core.optim import AdamW, split_decay_params                     # noqa: E402
from ai_core.training.datasets.text_dataset import TokenFileDataset    # noqa: E402
from ai_core.training.loss_fns import minigpt_loss                      # noqa: E402
from ai_core.training.schedule import lr_lambda                         # noqa: E402

# ---------------------------------------------------------------- 1. data
tb = glob.glob('/kaggle/input/**/train.bin', recursive=True)
vb = glob.glob('/kaggle/input/**/val.bin', recursive=True)
mb = glob.glob('/kaggle/input/**/meta.json', recursive=True)
if len(tb) != 1 or len(vb) != 1 or len(mb) != 1:
    raise SystemExit(f'can dung 1 train.bin/val.bin/meta.json, thay {len(tb)}/{len(vb)}/{len(mb)}')
meta = json.load(open(mb[0], encoding='utf-8'))
if meta.get('vocab_size') != 8192:
    raise SystemExit(f'vocab {meta.get("vocab_size")} != 8192')
TOK = '/tmp/tokens'
os.makedirs(TOK, exist_ok=True)
for src in (tb[0], vb[0]):                          # /kaggle/input la o mang: memmap doc ngau nhien cham
    dst = os.path.join(TOK, os.path.basename(src))
    if not os.path.exists(dst):
        shutil.copy(src, dst)
train_ds = TokenFileDataset(f'{TOK}/train.bin', CTX)
val_tokens = torch.from_numpy(TokenFileDataset(f'{TOK}/val.bin', CTX).data[:EVAL_TOKENS + 1].astype('int64'))
print(f'DATA OK: train {len(train_ds):,} windows x {CTX} | val eval tokens {EVAL_TOKENS:,}', flush=True)


def make(variant, seed):
    torch.manual_seed(seed)
    cfg = ModelConfig(name='minigpt', d_model=256, n_layers=4, n_heads=4, vocab_size=8192, context_len=1024,
                      dropout=0.0, pos_encoding=variant)
    return MiniGPT(cfg).cuda(), cfg


# ---------------------------------------------------------------- 2. sanity
os.chdir(CODE)
lines = []
for name, target in (('gradient check < 1e-4', 'ai_core/tests/test_gradient_check.py'),
                     ('AdamW parity < 1e-6', 'ai_core/tests/test_adamw_parity.py'),
                     ('pos_encoding (overfit, KV-cache, strict load)', 'ai_core/tests/test_pos_encoding.py')):
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', target], capture_output=True, text=True)
    lines.append(f"SANITY {name}: {'PASS' if r.returncode == 0 else 'FAIL'} | {r.stdout.strip().splitlines()[-1]}")
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-2000:])
g = torch.Generator().manual_seed(0)
xb, yb = map(torch.stack, zip(*[train_ds[int(i)] for i in torch.randint(len(train_ds), (4,), generator=g)]))
for variant in VARIANTS:                            # 4 real windows, 300 steps, warmup 100 -> 1e-3 (A1b lesson), loss < 0.05
    model, _ = make(variant, 0)
    opt = AdamW(split_decay_params(model), lr=1e-3, weight_decay=0.0)
    for step in range(300):
        for grp in opt.param_groups:
            grp['lr'] = 1e-3 * min(1.0, (step + 1) / 100)
        opt.zero_grad()
        loss = minigpt_loss(model, (xb.cuda(), yb.cuda()))
        loss.backward()
        opt.step()
    lines.append(f"SANITY overfit 1 batch that ({variant}, 4 x {CTX} token, 300 buoc): {'PASS' if loss.item() < 0.05 else 'FAIL'} | loss {loss.item():.4f}")
    del model, opt
torch.cuda.empty_cache()
print('\n'.join(lines), flush=True)
if any('FAIL' in s for s in lines):
    raise SystemExit('Sanity FAIL — khong train')


# ---------------------------------------------------------------- 3/4. train
def train(variant, seed, steps, bench=False):
    model, cfg = make(variant, seed)
    opt = AdamW(split_decay_params(model), lr=LR, weight_decay=WD)
    scaler = torch.amp.GradScaler('cuda')
    loader = torch.utils.data.DataLoader(train_ds, batch_size=BATCH, shuffle=True, drop_last=True, num_workers=2,
                                         generator=torch.Generator().manual_seed(seed))
    it, warm = iter(loader), int(WARM * steps)
    t0, log = time.time(), []
    for step in range(steps):
        for grp in opt.param_groups:
            grp['lr'] = LR * lr_lambda(step, warm, steps, MIN_RATIO)
        opt.zero_grad(set_to_none=True)
        total = 0.0
        for _ in range(ACCUM):
            try:
                batch = next(it)
            except StopIteration:
                it = iter(loader)
                batch = next(it)
            with torch.autocast('cuda', dtype=torch.float16):
                loss = minigpt_loss(model, (batch[0].cuda(non_blocking=True), batch[1].cuda(non_blocking=True))) / ACCUM
            scaler.scale(loss).backward()
            total += loss.item()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
        scaler.step(opt)
        scaler.update()
        if bench and step == 2:
            torch.cuda.synchronize()
            t0 = time.time()
        if not bench and (step + 1) % 500 == 0:
            log.append({'step': step + 1, 'train_loss': total, 'elapsed_s': round(time.time() - t0)})
            print(f'{variant} s{seed} step {step + 1}/{steps} loss {total:.4f} {time.time() - t0:.0f}s', flush=True)
    torch.cuda.synchronize()
    return model, cfg, (time.time() - t0) / max(1, steps - 3), log


@torch.no_grad()
def perplexity(model):
    model.eval()
    out = {}
    for ctx in EVAL_CTX:
        x = val_tokens[:-1].view(-1, ctx)
        y = val_tokens[1:].view(-1, ctx)
        nll, bs = 0.0, max(1, 8192 // ctx)
        for i in range(0, len(x), bs):
            logits, _ = model(x[i:i + bs].cuda())
            nll += torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), y[i:i + bs].cuda().reshape(-1),
                                                     reduction='sum').item()
        out[str(ctx)] = math.exp(nll / EVAL_TOKENS)
    model.train()
    return out


speed = {}
for variant in VARIANTS:
    _, _, speed[variant], _ = train(variant, 0, 23, bench=True)
per_run = max(speed.values())
n = min(MAX_N, int(BUDGET_H * 3600 * 0.9 / (len(SEEDS) * len(VARIANTS) * per_run)) // 500 * 500)
print(f'BENCH s/step {speed} -> N = {n} steps per run (fixed for all 6 runs, chosen before any training)', flush=True)
if n < 1000:
    raise SystemExit('N < 1000 — ngan sach khong du, dung (khong tu cat ngan sach)')

report = {'N': n, 'bench_s_per_step': speed, 'tokens_per_step': BATCH * ACCUM * CTX, 'eval_tokens': EVAL_TOKENS, 'runs': {}}
for seed in SEEDS:
    for variant in VARIANTS:
        model, cfg, sps, log = train(variant, seed, n)
        ppl = perplexity(model)
        params = sum(p.numel() for p in model.parameters())
        torch.save({'config': cfg.__dict__, 'state_dict': model.state_dict()}, f'{OUT}/pe_{variant}_s{seed}.pt')
        report['runs'][f'{variant}_s{seed}'] = {'variant': variant, 'seed': seed, 'ppl': ppl, 'params': params, 's_per_step': sps, 'log': log}
        json.dump(report, open(f'{OUT}/pe_eval.json', 'w'), indent=1)
        print(f'RESULT {variant} s{seed}: ppl {ppl} params {params:,}', flush=True)
        del model
        torch.cuda.empty_cache()
print('XONG — tai /kaggle/working/pe_eval.json + pe_*.pt ve', flush=True)
