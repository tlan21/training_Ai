"""T1.6c-e — fine-tune Mini-GPT tom tat tren wiki_summary (proxy cho sapo+than->tieu_de).

Why proxy: Binhvq News chua co; dung Wikipedia vi 96k cap (body->title) de thong lung
fine-tune pipeline + ROUGE + inference; thay news khi co dataset thuc (dataset_spec 3.5).

Input: /kaggle/input/wiki-summary-pairs/{train,val,test}.pairs.json (96k/12k/12k)
Ckpt: /kaggle/input/ai-core-minigpt-pretrain/minigpt/best.pt + bpe_vocab.json
       (DoD T1.6b perplexity 21.20, 246M token)
"""
import glob, json, os, sys, shutil, time, zipfile, pathlib

import torch, yaml

print("torch", torch.__version__, "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU", flush=True)
if not torch.cuda.is_available():
    raise SystemExit("Khong co GPU")
PREC = "bf16" if torch.cuda.is_bf16_supported(including_emulation=False) else "fp16"
print("precision:", PREC, flush=True)

# --- 0. nap ai_core
CODE = "/tmp/code"
if not os.path.isdir(f"{CODE}/ai_core"):
    z = glob.glob("/kaggle/input/**/ai_core.zip", recursive=True)
    pkg = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/ai_core/__init__.py", recursive=True) if os.path.isdir(os.path.join(os.path.dirname(p), "training"))]
    if z:
        import zipfile as zf
        with zf.ZipFile(z[0]) as f: f.extractall(CODE)
    elif pkg:
        shutil.copytree(pkg[0], f"{CODE}/ai_core")
    else:
        raise SystemExit("KHONG thay ai_core")
sys.path.insert(0, CODE)

from ai_core.config import ModelConfig, TrainConfig
from ai_core import build_model
from ai_core.tokenizer import BPETokenizer
from ai_core.training.datasets.summary_dataset import SummaryPairDataset
from ai_core.training import Trainer
from ai_core.training.loss_fns import LOSS_FNS
from ai_core.training.checkpoint import load_checkpoint
from torch.utils.data import DataLoader

def _pad(batch):
    m = max(x.shape[0] for x, _ in batch)
    return (torch.stack([torch.cat([x, torch.zeros(m - x.shape[0], dtype=x.dtype)]) for x,_ in batch]),
            torch.stack([torch.cat([y, torch.full((m - y.shape[0],), -100, dtype=y.dtype)]) for _,y in batch]))

# --- 1. du lieu
PAIRS_DIR = glob.glob("/kaggle/input/**/wiki_summary_train.pairs.json", recursive=True)
if not PAIRS_DIR:
    raise SystemExit("Thieu wiki_summary_train.pairs.json")
PAIRS_DIR = os.path.dirname(PAIRS_DIR[0])
print("pairs dir:", PAIRS_DIR, flush=True)
train_pairs = json.load(open(os.path.join(PAIRS_DIR, "wiki_summary_train.pairs.json"), encoding="utf-8"))
val_pairs   = json.load(open(os.path.join(PAIRS_DIR, "wiki_summary_val.pairs.json"), encoding="utf-8"))
test_pairs  = json.load(open(os.path.join(PAIRS_DIR, "wiki_summary_test.pairs.json"), encoding="utf-8"))
print(f"pairs train {len(train_pairs):,} val {len(val_pairs):,} test {len(test_pairs):,}", flush=True)

# --- 2. vocab + pretrain ckpt
vocab_cands = glob.glob("/kaggle/input/**/bpe_vocab.json", recursive=True)
# pretrain kernel may output to /kaggle/input/notebooks/...  glob ** already covers; also check local staging
vocab_cands += glob.glob("/tmp/**/bpe_vocab.json", recursive=True)
# also load from ai-core code itself (ai-core.zip may contain bpe_vocab)
# and from pretrain ckpt's bpe_vocab field fallback handled below
# prefer pretrain kernel output; also check working
for p in ["/kaggle/working/bpe/bpe_vocab.json", "E:/checkpointhighlight/minigpt_pretrain/bpe_vocab.json"]:
    if os.path.exists(p): vocab_cands.append(p)
ckpt_cands = glob.glob("/kaggle/input/**/minigpt/best.pt", recursive=True) + glob.glob("/kaggle/input/**/best.pt", recursive=True)
ckpt_cands += glob.glob("/kaggle/input/ai-core-minigpt-pretrain/**/best.pt", recursive=True)
ckpt_cands = [p for p in ckpt_cands if "minigpt" in p.lower() or "pretrain" in p.lower() or True][:10]
print("vocab cands", vocab_cands[:3], flush=True)
print("ckpt cands", ckpt_cands[:3], flush=True)
vocab_path = None
for p in vocab_cands:
    if "minigpt" in p.lower() or "pretrain" in p.lower():
        vocab_path = p; break
# fallback: extract bpe_vocab from ckpt itself if no file found
if not vocab_cands:
    print("no bpe_vocab.json found — will extract from ckpt bpe_vocab field", flush=True)
else:
    vocab_path = vocab_path or vocab_cands[0]
# pick ckpt that is minigpt
ckpt_path = None
for p in ckpt_cands:
    try:
        ck = torch.load(p, map_location="cpu")
        if ck.get("config", {}).get("name") == "minigpt":
            ckpt_path = p; break
    except: pass
ckpt_path = ckpt_path or ckpt_cands[0]
print("vocab:", vocab_path, flush=True)
print("ckpt:", ckpt_path, flush=True)

# ckpt load first if vocab missing — ckpt contains bpe_vocab
ckpt = load_checkpoint(ckpt_path, map_location="cpu")
if not vocab_cands:
    # write temp bpe json from ckpt
    import tempfile as _tmp
    tok_dict = ckpt.get("bpe_vocab")
    if not tok_dict:
        raise SystemExit("ckpt has no bpe_vocab and no file found")
    vocab_path = "/tmp/bpe_vocab.json"
    json.dump(tok_dict, open(vocab_path, "w", encoding="utf-8"))
tok = BPETokenizer.load(vocab_path)
print(f"pretrain metrics {ckpt.get('metrics')} params {sum(p.numel() for p in ckpt['state_dict'].values()):,}", flush=True)

# also copy bpe to working for evaluate
os.makedirs("/kaggle/working/bpe", exist_ok=True)
import shutil as _sh
_sh.copy(vocab_path, "/kaggle/working/bpe/bpe_vocab.json")

# --- 3. dataset
tr_ds = SummaryPairDataset(train_pairs, tok, fmt="title", context_len=1024)
va_ds = SummaryPairDataset(val_pairs, tok, fmt="title", context_len=1024)
tr = DataLoader(tr_ds, batch_size=8, shuffle=True, collate_fn=_pad)
va = DataLoader(va_ds, batch_size=8, collate_fn=_pad)
print(f"dataset len tr {len(tr_ds)} va {len(va_ds)} sample x {tr_ds[0][0].shape} -> loss_tokens {(tr_ds[0][1]!=-100).sum().item()}", flush=True)

cfg = ModelConfig(**ckpt["config"])
model = build_model(cfg.name, cfg)
model.load_state_dict(ckpt["state_dict"])
print("warm start loaded", flush=True)

# --- 4. train (finetune lr 1e-4 per minigpt_finetune_summary.yaml)
tc = TrainConfig(model="minigpt", lr=1e-4, weight_decay=0.1, batch_size=8, grad_accum=8, max_steps=8000, warmup_ratio=0.03, min_lr_ratio=0.10, precision=PREC, seed=1337, metric_name="", ckpt_dir="/kaggle/working/ckpt_minigpt_ft", log_dir="")
print(f"TrainConfig {tc.max_steps} steps bs{tc.batch_size}x{tc.grad_accum} lr{tc.lr} {tc.precision}", flush=True)
trainer = Trainer(model, tr, va, tc, loss_fn=LOSS_FNS["minigpt"], model_cfg=cfg, bpe_vocab=json.load(open(vocab_path, encoding="utf-8")), metadata={})
t0 = time.time()
stats = trainer.train()
print(f"train done in {(time.time()-t0)/3600:.2f}h {stats}", flush=True)

# --- 5. ROUGE on test (generate greedy, compare to target)
from ai_core.scripts.evaluate import rouge_l

# load best (last if no eval metric)
best_pt = "/kaggle/working/ckpt_minigpt_ft/minigpt/best.pt"
if not os.path.exists(best_pt):
    best_pt = "/kaggle/working/ckpt_minigpt_ft/minigpt/last.pt"
bk = load_checkpoint(best_pt, map_location="cpu")
model.load_state_dict(bk["state_dict"])
model.eval()
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def _greedy(prompt_ids, max_new=32):
    model.eval()
    with torch.no_grad():
        return model.generate(prompt_ids.to(device), max_new_tokens=max_new, temperature=0.0)

# build control prefix ids for "title"
fmt = "<title>"
# SummaryPairDataset encodes as <title> + src + <eos> + tgt + <eos>; we need to split
# Instead re-derive prompt from raw pairs: tok.encode("<title> "+src) then generate
N = min(500, len(test_pairs))
rouges = []
samples = []
for i in range(N):
    src, tgt = test_pairs[i]
    prompt_ids = torch.tensor(tok.encode(fmt + " " + src), dtype=torch.long)
    if prompt_ids.numel() > 1023:
        prompt_ids = prompt_ids[:1023]
    gen = _greedy(prompt_ids.unsqueeze(0), max_new=32)
    # gen includes prompt; strip prompt
    gen_ids = gen[0, prompt_ids.numel():].tolist()
    # cut at eos
    eos = tok.special_tokens["<eos>"]
    if eos in gen_ids:
        gen_ids = gen_ids[:gen_ids.index(eos)]
    hyp = tok.decode(gen_ids).strip()
    ref = tgt.strip()
    # ROUGE-L expects word-level; our rouge_l splits on whitespace
    rouges.append(rouge_l(ref, hyp))
    if i < 5:
        samples.append((ref, hyp))

import statistics
mean = statistics.mean(rouges) if rouges else 0
print(f"ROUGE-L test (n={N}) mean {mean:.4f} | median {statistics.median(rouges):.4f}", flush=True)
for ref, hyp in samples:
    print(f"  ref: {ref[:80]}\n  hyp: {hyp[:80]}\n---", flush=True)

# --- 6. Lead-1 baseline (first sentence of input as title proxy) for comparison
lead_rouges = []
for i in range(N):
    src, tgt = test_pairs[i]
    lead = src.split(".")[0].strip()[:80]
    lead_rouges.append(rouge_l(tgt.strip(), lead))
print(f"Lead-1 ROUGE-L mean {statistics.mean(lead_rouges):.4f} (baseline)", flush=True)
print(f"Delta vs Lead-1: {mean - statistics.mean(lead_rouges):+.4f} {'PASS' if mean > statistics.mean(lead_rouges) else 'FAIL'}", flush=True)

# save json for docs
out = {"rouge_l_mean": mean, "rouge_l_median": statistics.median(rouges), "lead_rouge_l": statistics.mean(lead_rouges), "delta": mean - statistics.mean(lead_rouges), "n": N, "pretrain_ppl": ckpt.get("metrics", {}).get("perplexity"), "train_stats": stats}
json.dump(out, open("/kaggle/working/minigpt_ft_eval.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("saved /kaggle/working/minigpt_ft_eval.json", out, flush=True)
print("XONG — tai /kaggle/working/ckpt_minigpt_ft/minigpt/best.pt + minigpt_ft_eval.json ve TRUOC khi push ban sau", flush=True)
