# 01 — KẾ HOẠCH TRIỂN KHAI AI CORE (TRÁI TIM DỰ ÁN)
*Plan con của @00_master_plan.md. Mọi hyperparameter khớp @model_spec.md, dữ liệu/nhãn khớp @dataset_spec.md, metric/test khớp @evaluation_plan.md, nền tảng @kien_truc_va_thuat_toan_ai.md. Xung đột → master_plan + model_spec thắng.*

> Phạm vi: package Python thuần `ai-core/ai_core/` — thuật toán nguyên thủy, 6 model tự train, không dính web/DB. Checkpoint xuất ra cho `inference-service/` nạp (endpoint mục 2.4 master plan). CẤM pretrained mọi hình thức (@dataset_spec.md mục 0). Chỉ dùng PyTorch làm nền tensor + autograd.

---

## 0. Nguyên tắc thiết kế code (bắt buộc)

- **Type hints đầy đủ**, docstring 1–3 dòng, chú thích shape tensor từng chiều bằng comment `# (B, T, D)`.
- **Không over-engineer:** không abstraction cho code dùng 1 lần, không config cho hằng số không đổi, không factory.
- **1 khối Transformer dùng chung** (`primitives/block.py`) cấu hình bằng tham số — mọi model tái dùng, không copy-paste.
- **Fast-path song song:** MultiHeadAttention có cờ `use_sdpa` — bản viết tay `softmax(QKᵀ/√d)V` để trình bày luận án + kiểm chứng, bản `F.scaled_dot_product_attention` để train nhanh; unit test ép 2 bản bằng nhau (@model_spec.md mục 0).
- **Quy ước tensor:** batch-first `(B, T, D)`; ảnh `(B, C, H, W)`; audio mel `(B, n_mels, T)`.
- **Seed cố định** ghi trong config YAML; mọi thí nghiệm reproduce được.

---

## 1. Cây thư mục `ai-core/` đầy đủ

```
ai-core/
├── pyproject.toml                  # metadata package + deps (torch, numpy, pyyaml, tensorboard, soundfile, decord)
├── README.md                       # cách train/test/export từng model
└── ai_core/
    ├── __init__.py                 # export version + factory build_model(name, cfg)
    ├── config.py                   # dataclass ModelConfig, TrainConfig; load/dump YAML
    ├── primitives/
    │   ├── __init__.py             # re-export MHA, RMSNorm, SwiGLU, RoPE, TransformerBlock, PositionalEmbedding2D
    │   ├── attention.py            # MultiHeadAttention (softmax tay + SDPA fast-path, causal, KV-cache, cross-attn)
    │   ├── rmsnorm.py              # RMSNorm pre-norm
    │   ├── swiglu.py               # SwiGLU FFN (hidden = 8/3·d làm tròn bội 64)
    │   ├── rope.py                 # RoPE: build_rope_cache + apply_rope lên q/k
    │   ├── embedding.py            # PositionalEmbedding2D (ViT) + TiedEmbedding (Mini-GPT) — BỔ SUNG ngoài list master plan
    │   └── block.py                # TransformerBlock pre-norm (self/cross), khởi tạo GPT-2 style
    ├── optim/
    │   ├── __init__.py
    │   └── adamw.py                # AdamW tự viết (moment m,v, bias correction, decoupled WD, no-decay bias/norm)
    ├── tokenizer/
    │   ├── __init__.py
    │   └── bpe.py                  # BPETokenizer: train (đếm cặp + merge lặp), encode/decode, save/load JSON, vocab 8192
    ├── audio/
    │   ├── __init__.py
    │   ├── mel.py                  # FFT tự cài → Mel filterbank 80 bins (công thức mel scale) + SpecAugment
    │   └── features.py             # đặc trưng 64-d/giây cho highlight (RMS energy, pitch proxy, delta)
    ├── vision/
    │   ├── __init__.py
    │   ├── patchify.py             # cắt ảnh 224² thành patch 16×16 → (B, 196, patch_dim); dựng token [CLS]
    │   └── augment.py              # RandomResizedCrop, flip, color jitter (thuần phép tensor, tự code)
    ├── models/
    │   ├── __init__.py
    │   ├── vit.py                  # ViT phân loại 10–20 lớp (d=256, 6 layer, 8 head, ~5M)
    │   ├── siamese.py              # SiameseViT: backbone ViT dùng chung + projection 256→128, InfoNCE τ=0.07
    │   ├── asr_ctc.py              # Conv subsample ×4 + encoder (d=256, 8 layer) + CTC head 95 ký tự
    │   ├── highlight_fusion.py     # 2 self-attn/nhánh + 2 cross-attn → sigmoid 0–1/giây (~4M)
    │   ├── minigpt.py              # decoder-only d=384, 6 layer, ctx 1024, KV-cache, weight tying (~14M)
    │   ├── two_tower.py            # MLP 3 tầng/tower → 128, BPR loss (<1M)
    │   └── ctc.py                  # CTC loss forward (log-alpha DP) + greedy/beam decode — tự cài
    ├── training/
    │   ├── __init__.py
    │   ├── trainer.py              # Trainer: bf16 autocast, grad-accum, clip 1.0, ckpt best/last, TensorBoard, seed
    │   ├── schedule.py             # warmup tuyến tính 3% + cosine decay về 10% LR đỉnh
    │   ├── checkpoint.py           # save/load dict {config, state_dict, bpe_vocab?, metrics}
    │   ├── configs/
    │   │   ├── vit.yaml
    │   │   ├── siamese.yaml
    │   │   ├── asr_ctc.yaml
    │   │   ├── highlight_fusion.yaml
    │   │   ├── minigpt_pretrain.yaml
    │   │   ├── minigpt_finetune_summary.yaml
    │   │   └── two_tower.yaml
    │   └── datasets/
    │       ├── __init__.py
    │       ├── vit_dataset.py          # keyframe 1fps + nhãn video-level, split 80/10/10 theo video
    │       ├── siamese_dataset.py      # sinh cặp dương shot-boundary (histogram màu) + in-batch neg
    │       ├── asr_dataset.py          # VIVOS/CommonVoice → mel 80 + nhãn char, collate CTC (pad + lengths)
    │       ├── highlight_dataset.py    # weak-label bằng cross-correlation Mel; cửa sổ 120s stride 60s
    │       ├── text_dataset.py         # corpus text → chunk 1024 token BPE cho pretrain next-token
    │       ├── summary_dataset.py      # cặp (sapo+thân → tiêu đề) fine-tune tóm tắt
    │       └── movielens_dataset.py    # MovieLens-100k → triple (user, pos, neg) cho BPR
    ├── scripts/
    │   ├── train.py                # entrypoint: python -m ai_core.scripts.train --config configs/vit.yaml
    │   ├── train_bpe.py            # train BPE 8192 trên Wikipedia vi + báo chí → vocab.json
    │   ├── build_weak_labels.py    # dựng nhãn highlight nhị phân/giây từ bản phát sóng (cross-correlation)
    │   └── evaluate.py             # tính metric test set theo @evaluation_plan.md mục 1
    ├── checkpoints/                # {vit,siamese,asr_ctc,highlight_fusion,minigpt,two_tower}/{best,last}.pt
    └── tests/
        ├── __init__.py
        ├── test_gradient_check.py      # finite-diff vs autograd < 1e-4 (fp64)
        ├── test_adamw_parity.py        # parity torch.optim.AdamW < 1e-6 sau 100 bước
        ├── test_overfit_one_batch.py   # mọi model loss ≈ 0 trên 1 batch
        ├── test_bpe_roundtrip.py       # encode→decode 100% trên 10.000 câu
        ├── test_sdpa_parity.py         # MHA tay vs SDPA bằng nhau
        ├── test_ctc_parity.py          # CTC forward vs torch.nn.CTCLoss
        └── test_shapes.py              # smoke test forward shape từng model
```

---

## 2. Đặc tả module `primitives/`

Signature Python đầy đủ, kèm shape. Ký hiệu: `B`=batch, `T`=seq len, `D`=d_model, `H`=n_heads, `Dh`=D//H.

### 2.1. `attention.py` — MultiHeadAttention

```python
class MultiHeadAttention(nn.Module):
    """softmax(QKᵀ/√Dh)V viết tay; use_sdpa=True chuyển sang F.scaled_dot_product_attention.
    Hỗ trợ self-attn, cross-attn (kv_input khác), causal mask, KV-cache khi generate."""

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        dropout: float = 0.0,
        causal: bool = False,
        use_sdpa: bool = True,
        use_rope: bool = False,   # True cho text/audio; False cho ViT (dùng PositionalEmbedding2D)
    ) -> None: ...
    # wq, wk, wv, wo: nn.Linear(d_model, d_model, bias=False)

    def forward(
        self,
        x: torch.Tensor,                          # (B, T, D) — query source
        kv_input: torch.Tensor | None = None,     # (B, S, D) cross-attn; None → self-attn (S=T)
        attn_mask: torch.Tensor | None = None,    # (B, 1, T, S) bool/float; None → causal tự sinh nếu causal=True
        rope_cache: tuple[torch.Tensor, torch.Tensor] | None = None,  # (cos, sin) khi use_rope
        kv_cache: KVCache | None = None,          # append k,v khi generate từng bước
    ) -> torch.Tensor:                            # (B, T, D)
        ...
    # Nội bộ: reshape → (B, H, T, Dh); nếu không use_sdpa:
    #   scores = q @ k.transpose(-2,-1) / sqrt(Dh)   # (B, H, T, S)
    #   scores = scores.masked_fill(mask, -inf); a = softmax(scores, -1); out = a @ v


class KVCache:
    """Bộ nhớ k,v cho decoder generate. k,v: (B, H, T_cache, Dh)."""
    def __init__(self, max_len: int, n_layers: int, ...): ...
    def update(self, layer_idx: int, k: torch.Tensor, v: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]: ...
    def reset(self) -> None: ...
```

### 2.2. `rmsnorm.py` — RMSNorm

```python
class RMSNorm(nn.Module):
    """x / sqrt(mean(x²) + eps) * weight. Pre-norm, không có bias."""
    def __init__(self, d_model: int, eps: float = 1e-6) -> None: ...   # weight: (D,) init 1.0
    def forward(self, x: torch.Tensor) -> torch.Tensor: ...            # (B, T, D) → (B, T, D)
```

### 2.3. `swiglu.py` — SwiGLU FFN

```python
class SwiGLU(nn.Module):
    """SwiGLU: (silu(x·W_gate) * (x·W_up))·W_down. hidden = round_to_multiple(8/3·d_model, 64)."""
    def __init__(self, d_model: int, hidden: int | None = None) -> None: ...
    # w_gate, w_up: Linear(D, hidden, bias=False); w_down: Linear(hidden, D, bias=False)
    def forward(self, x: torch.Tensor) -> torch.Tensor: ...            # (B, T, D) → (B, T, D)

def swiglu_hidden(d_model: int) -> int:  # round(8/3·d_model / 64) * 64
    ...
```

### 2.4. `rope.py` — Rotary Position Embedding

```python
def build_rope_cache(seq_len: int, head_dim: int, base: float = 10000.0,
                     device=None, dtype=torch.float32) -> tuple[torch.Tensor, torch.Tensor]:
    """Trả (cos, sin) shape (seq_len, head_dim) để cache 1 lần/độ dài."""
    ...

def apply_rope(q: torch.Tensor, k: torch.Tensor,
               cos: torch.Tensor, sin: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Xoay từng cặp chiều của q,k. q,k: (B, H, T, Dh); cos,sin: (T, Dh)."""
    ...   # q_rot = q*cos + rotate_half(q)*sin
```

### 2.5. `embedding.py` — PositionalEmbedding2D + TiedEmbedding

> BỔ SUNG ngoài danh sách file master plan (master plan liệt kê primitives không có file này). Cần cho ViT (pos emb 2D học được — @model_spec.md mục 1) và Mini-GPT (weight tying). Không đổi file nào trong contract.

```python
class PositionalEmbedding2D(nn.Module):
    """Positional embedding học được cho ViT: (1, n_patches+1, D) gồm cả vị trí [CLS]."""
    def __init__(self, n_patches: int, d_model: int) -> None: ...   # pos: nn.Parameter(1, n_patches+1, D)
    def forward(self, x: torch.Tensor) -> torch.Tensor: ...          # (B, N+1, D) → cộng pos

class TiedEmbedding(nn.Module):
    """Embedding token dùng chung trọng số với lớp output logits (weight tying) cho Mini-GPT."""
    def __init__(self, vocab_size: int, d_model: int) -> None: ...   # emb: (V, D)
    def encode(self, ids: torch.Tensor) -> torch.Tensor: ...         # (B, T) → (B, T, D)
    def logits(self, h: torch.Tensor) -> torch.Tensor: ...           # (B, T, D) → (B, T, V) dùng emb.T
```

### 2.6. `block.py` — TransformerBlock (pre-norm)

```python
class TransformerBlock(nn.Module):
    """Pre-norm block: x = x + Attn(RMSNorm(x)); x = x + SwiGLU(RMSNorm(x)).
    cross_attn=True thêm nhánh cross-attention (dùng cho Highlight Fusion)."""
    def __init__(
        self,
        d_model: int,
        n_heads: int,
        causal: bool = False,
        use_rope: bool = False,
        cross_attn: bool = False,
        n_layers_total: int = 1,   # scale residual init 1/sqrt(2·n_layers)
        dropout: float = 0.0,
    ) -> None: ...

    def forward(
        self,
        x: torch.Tensor,                       # (B, T, D)
        kv_input: torch.Tensor | None = None,  # (B, S, D) khi cross_attn
        attn_mask: torch.Tensor | None = None,
        rope_cache=None,
        kv_cache=None,
        layer_idx: int = 0,
    ) -> torch.Tensor:                         # (B, T, D)
        ...
```

Khởi tạo: mọi Linear `Normal(0, 0.02)`; trọng số của `w_o`/`w_down` (residual output) scale thêm `1/√(2·n_layers)` (GPT-2 style, @model_spec.md mục 1).

---

## 3. `optim/adamw.py` — AdamW tự viết

Thuật toán cập nhật từng bước (β1=0.9, β2=0.95, wd=0.1, eps=1e-8 — @model_spec.md mục 3):

```
Với mỗi param p có grad g tại bước t:
  1. m ← β1·m + (1-β1)·g                      # first moment
  2. v ← β2·v + (1-β2)·g²                      # second moment
  3. m̂ ← m / (1 - β1ᵗ)                         # bias correction
  4. v̂ ← v / (1 - β2ᵗ)
  5. p ← p - lr · m̂ / (√v̂ + eps)              # bước Adam
  6. p ← p - lr · wd · p                        # decoupled weight decay (CHỈ áp cho param 2D+, KHÔNG cho bias/norm)
```

```python
class AdamW(torch.optim.Optimizer):
    def __init__(self, params, lr: float, betas=(0.9, 0.95),
                 eps: float = 1e-8, weight_decay: float = 0.1) -> None: ...
    @torch.no_grad()
    def step(self, closure=None) -> float | None: ...   # trả loss nếu có closure

def split_decay_params(model: nn.Module) -> list[dict]:
    """Tách 2 nhóm: param ndim>=2 → weight_decay; bias + RMSNorm weight → weight_decay=0."""
    ...
```

**Test parity** (`test_adamw_parity.py`): bài hồi quy tuyến tính nhỏ, chạy 100 bước song song bản tự viết và `torch.optim.AdamW` (cùng seed, cùng no-decay grouping) → `max|w_mine - w_torch| < 1e-6` (@evaluation_plan.md 2.3).

---

## 4. `tokenizer/bpe.py` — BPE tự viết (vocab 8192)

Thuật toán train (byte-level, @dataset_spec.md 3.5):

```
1. Khởi tạo vocab = 256 byte cơ bản + token đặc biệt (<pad>, <bos>, <eos>, <unk>).
2. Biểu diễn corpus thành list[list[int]] (mỗi từ = dãy byte).
3. LẶP tới khi |vocab| = 8192:
   a. Đếm tần suất mọi cặp liền kề (pair, count) trên toàn corpus.
   b. Chọn cặp tần suất cao nhất → merge thành token mới id = |vocab|.
   c. Ghi merge (a,b)→id vào bảng merges; thay mọi (a,b) trong corpus bằng id.
4. Lưu {vocab, merges, special_tokens} ra JSON.
```

```python
class BPETokenizer:
    def __init__(self, vocab_size: int = 8192) -> None: ...
    def train(self, corpus: Iterable[str], min_freq: int = 2) -> None: ...
    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]: ...
    def decode(self, ids: list[int]) -> str: ...
    def save(self, path: str) -> None: ...                  # JSON: {vocab, merges, specials}
    @classmethod
    def load(cls, path: str) -> "BPETokenizer": ...
    @property
    def vocab_size(self) -> int: ...
```

**Test** (`test_bpe_roundtrip.py`): `decode(encode(s)) == s` cho 10.000 câu ngẫu nhiên từ corpus → 100% (@evaluation_plan.md 2.3).

---

## 5. `audio/` — Mel + đặc trưng highlight

### 5.1. `mel.py` — FFT + Mel filterbank 80 bins (tự cài)

Công thức mel scale: `mel(f) = 2595·log10(1 + f/700)`; `hz(m) = 700·(10^(m/2595) - 1)`. FFT 400, hop 160, 16kHz (@model_spec.md 2 chi tiết ASR).

```python
def stft(signal: torch.Tensor, n_fft: int = 400, hop: int = 160,
         window: torch.Tensor | None = None) -> torch.Tensor:
    """Short-time FFT tự cài (torch.fft.rfft trên frame trượt). → power spectrogram (n_freq, T)."""
    ...

def mel_filterbank(n_mels: int = 80, n_fft: int = 400, sr: int = 16000,
                   fmin: float = 0.0, fmax: float = 8000.0) -> torch.Tensor:
    """Ma trận tam giác chồng lấn theo mel scale. → (n_mels, n_fft//2+1)."""
    ...

def log_mel_spectrogram(signal: torch.Tensor, n_mels: int = 80, **kw) -> torch.Tensor:
    """log(mel_fb @ power_stft + 1e-6). → (n_mels, T)."""
    ...

class SpecAugment(nn.Module):
    """Che ngẫu nhiên F dải tần + T dải thời gian (tự code)."""
    def __init__(self, freq_mask: int = 15, time_mask: int = 35, n_freq: int = 2, n_time: int = 2): ...
    def forward(self, mel: torch.Tensor) -> torch.Tensor: ...   # (n_mels, T) → cùng shape
```

### 5.2. `features.py` — đặc trưng 64-d/giây cho Highlight

Mỗi giây audio → vector 64-d (token audio nhánh fusion, @model_spec.md 2):

```python
def audio_features_per_second(signal: torch.Tensor, sr: int = 16000) -> torch.Tensor:
    """Ghép: RMS energy, log-energy, zero-crossing rate, pitch proxy (đỉnh tự tương quan),
    16 hệ số mel trung bình + delta (sai phân bậc 1) → pad/chiếu về 64-d. → (n_seconds, 64)."""
    ...
```

---

## 6. `models/` — kiến trúc layer-by-layer

Mọi model dùng `TransformerBlock`. Params/VRAM/hyperparameter đúng @model_spec.md mục 2.

### 6.1. `vit.py` — ViT phân loại

- **Input:** ảnh `(B, 3, 224, 224)` → `patchify` patch 16×16 → 196 patch → Linear → `(B, 196, 256)`; prepend token `[CLS]` học được → `(B, 197, 256)`; cộng `PositionalEmbedding2D`.
- **Backbone:** 6× `TransformerBlock(d_model=256, n_heads=8, causal=False, use_rope=False)`.
- **Head:** RMSNorm → lấy token `[CLS]` `(B, 256)` → Linear(256, n_classes).
- **Loss:** Cross-Entropy.
- **Output forward:** `logits (B, n_classes)` + `cls_embedding (B, 256)` (embedding 256 cho endpoint `/v1/vision/completions`, master plan 2.4).

```python
class ViT(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None: ...
    def forward(self, images: torch.Tensor,
                return_embedding: bool = False) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]: ...
```

### 6.2. `siamese.py` — SiameseViT (Visual Search)

- **Backbone dùng chung** ViT (`return_embedding` → `(B, 256)`), thêm **projection head 256→128** (Linear→GELU→Linear), L2-normalize → `(B, 128)` nạp Milvus.
- **Loss InfoNCE** in-batch negatives, τ=0.07: `L = -log( exp(sim(a,p)/τ) / Σ_j exp(sim(a,j)/τ) )`, sim = cosine.
- Cặp dương/âm sinh trong `siamese_dataset.py` (mục 7).

```python
class SiameseViT(nn.Module):
    def __init__(self, cfg: ModelConfig, vit_backbone: ViT | None = None) -> None: ...
    def encode(self, images: torch.Tensor) -> torch.Tensor: ...              # (B, 3,224,224) → (B, 128) L2-norm
    def forward(self, view_a: torch.Tensor, view_b: torch.Tensor) -> torch.Tensor: ...  # → loss scalar (InfoNCE)
```

### 6.3. `asr_ctc.py` + `ctc.py` — ASR Encoder + CTC

- **Front-end:** log-mel 80 `(B, 80, T)` → 2× Conv2D stride 2 (subsample ×4) → Linear → `(B, T/4, 256)`.
- **Encoder:** 8× `TransformerBlock(d_model=256, n_heads=8, use_rope=True)` (non-causal).
- **Head:** Linear(256, 95) → log_softmax → `(B, T/4, 95)`.
- **Loss:** CTC tự cài (log-alpha forward DP), đối chiếu `torch.nn.CTCLoss`.
- **Decode:** greedy (collapse repeat + bỏ blank); beam search (`ctc.py`).

```python
class ASR_CTC(nn.Module):
    def __init__(self, cfg: ModelConfig, n_chars: int = 95) -> None: ...
    def forward(self, mel: torch.Tensor, mel_lengths: torch.Tensor
                ) -> tuple[torch.Tensor, torch.Tensor]: ...   # log_probs (B, T', 95), out_lengths (B,)

# ctc.py
def ctc_loss(log_probs, targets, input_lengths, target_lengths, blank: int = 0) -> torch.Tensor: ...
def ctc_greedy_decode(log_probs, lengths, blank: int = 0) -> list[list[int]]: ...
def ctc_beam_decode(log_probs, lengths, beam_width: int = 10, blank: int = 0) -> list[list[int]]: ...
```

`out_segments` (timestamp câu) suy từ vị trí frame non-blank × hop×4/sr — service dùng dựng `subtitles.segments` (master plan 2.2).

### 6.4. `highlight_fusion.py` — Highlight Fusion (đóng góp chính)

- **Input mỗi cửa sổ 120s:** nhánh visual `(B, 120, 256)` (ViT embedding/giây, backbone đóng băng) + nhánh audio `(B, 120, 64)` → Linear chiếu về 256.
- **2 self-attn/nhánh:** 2× `TransformerBlock(256, 8)` cho visual; 2× cho audio (non-causal).
- **2 cross-attn:** visual←audio, audio←visual (`cross_attn=True`), rồi hợp → head.
- **Head:** RMSNorm → Linear(256, 1) → sigmoid → `(B, 120)` điểm 0–1/giây.
- **Loss:** BCE với `pos_weight` (class imbalance ~5%, @dataset_spec.md 3.4).
- **Ghép cửa sổ:** stride 60s, trung bình vùng chồng (làm mượt) → chuỗi điểm cả video; scale ×100 khi trả API (thang 0–100, master plan 2.6).

```python
class HighlightFusion(nn.Module):
    def __init__(self, cfg: ModelConfig, vision_dim: int = 256, audio_dim: int = 64) -> None: ...
    def forward(self, vision_tokens: torch.Tensor, audio_tokens: torch.Tensor) -> torch.Tensor: ...
    # (B,120,256),(B,120,64) → (B,120) sigmoid
```

### 6.5. `minigpt.py` — Mini-GPT (decoder-only)

- **d_model 384, 6 layer, 6 head, ctx 1024, vocab BPE 8192**, `TiedEmbedding`, RoPE, causal mask.
- **Forward train:** `(B, T)` ids → `(B, T, 8192)` logits; loss Cross-Entropy shift-by-one.
- **Generate:** KV-cache tự code, sampling top-k + temperature.
- **Map-reduce >1024 token:** service chia transcript thành đoạn ~900 token, tóm tắt từng đoạn, nối rồi tóm tắt lần cuối (master plan 2.4 / @model_spec.md 2). Hàm helper `summarize_long` ở tầng service, model chỉ lo generate 1 đoạn.

```python
class MiniGPT(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None: ...
    def forward(self, ids: torch.Tensor, targets: torch.Tensor | None = None
                ) -> tuple[torch.Tensor, torch.Tensor | None]: ...   # logits (B,T,V), loss?
    @torch.no_grad()
    def generate(self, prompt_ids: torch.Tensor, max_new_tokens: int,
                 temperature: float = 0.8, top_k: int = 40, eos_id: int | None = None
                 ) -> torch.Tensor: ...   # dùng KVCache
```

### 6.6. `two_tower.py` — Two-Tower Recommender

- **User tower:** MLP 3 tầng (one-hot danh mục ưa thích + thống kê hành vi) → 128, L2-norm.
- **Video tower:** MLP 3 tầng (ViT embedding trung bình + danh mục) → 128, L2-norm.
- **Loss BPR:** `-log σ(sim(u,pos) - sim(u,neg))`, sim = inner product.
- Vector 128 nạp Milvus (IP metric).

```python
class TwoTower(nn.Module):
    def __init__(self, cfg: ModelConfig, user_dim: int, video_dim: int) -> None: ...
    def user_embed(self, x: torch.Tensor) -> torch.Tensor: ...    # (B, user_dim) → (B, 128) L2-norm
    def video_embed(self, x: torch.Tensor) -> torch.Tensor: ...   # (B, video_dim) → (B, 128) L2-norm
    def forward(self, user, pos_video, neg_video) -> torch.Tensor: ...  # → BPR loss
```

---

## 7. `training/`

### 7.1. `trainer.py` — Trainer

```python
@dataclass
class TrainConfig:
    model: str                      # vit|siamese|asr_ctc|highlight_fusion|minigpt|two_tower
    lr: float                       # đỉnh: vit/siamese 3e-4, asr 5e-4, fusion 3e-4, minigpt 6e-4
    weight_decay: float = 0.1
    betas: tuple = (0.9, 0.95)
    batch_size: int = 32
    grad_accum: int = 1             # minigpt = 8 (batch hiệu dụng 64)
    max_steps: int = 0
    warmup_ratio: float = 0.03
    min_lr_ratio: float = 0.10      # cosine decay về 10% LR đỉnh
    grad_clip: float = 1.0
    precision: str = "bf16"         # autocast bf16, master weights fp32
    seed: int = 1337
    ckpt_dir: str = "checkpoints/"
    log_dir: str = "runs/"
    eval_every: int = 0
    metric_name: str = ""           # metric chọn best (accuracy, wer↓, f1, rouge_l...)

class Trainer:
    def __init__(self, model: nn.Module, train_loader, val_loader,
                 cfg: TrainConfig, compute_metric: Callable | None = None) -> None: ...
    def train(self) -> dict: ...    # vòng train + eval; lưu best/last; trả metrics cuối
    def _step(self, batch) -> float: ...   # autocast, backward, accum, clip, optimizer.step
```

- bf16 autocast; **fp32 master weights**; `torch.nn.utils.clip_grad_norm_(…, 1.0)`.
- LR từ `schedule.py`; TensorBoard log loss + LR + metric mỗi step/epoch.
- Seed cố định (`torch`, `numpy`, `random`, `cudnn.deterministic`).

### 7.2. `schedule.py`

```python
def lr_lambda(step: int, warmup_steps: int, max_steps: int, min_ratio: float = 0.10) -> float:
    """Linear warmup [0→1] trong warmup_steps, rồi cosine decay [1→min_ratio] tới max_steps."""
    ...
```

### 7.3. `datasets/` (khớp @dataset_spec.md)

| File | Nguồn | Nhãn/cặp | Ghi chú |
|---|---|---|---|
| `vit_dataset.py` | keyframe 1fps | nhãn video-level | split 80/10/10 **theo video**; loại frame đen (ngưỡng std pixel) |
| `siamese_dataset.py` | keyframe cùng kho | cặp dương: 2 frame liền cùng shot (histogram màu) + augment; âm: in-batch | self-supervised |
| `asr_dataset.py` | VIVOS + CommonVoice vi | transcript char (~95 ký tự) | resample 16kHz mono; collate CTC (pad + input/target lengths) |
| `highlight_dataset.py` | trận full + bản phát sóng | **weak-label cross-correlation Mel** (script `build_weak_labels.py`) | cửa sổ 120s stride 60s; test 5 trận nhãn người |
| `text_dataset.py` | Wikipedia vi + báo | next-token | chunk 1024 token BPE |
| `summary_dataset.py` | báo chí | cặp (sapo+thân → tiêu đề) | fine-tune tóm tắt |
| `movielens_dataset.py` | MovieLens-100k | triple (user, pos, neg) BPR | split theo thời gian |

**Weak-label chi tiết** (`build_weak_labels.py`): với mỗi đoạn bản highlight, tính log-mel; trượt cross-correlation trên log-mel trận full → tìm offset argmax; giây thuộc đoạn khớp → nhãn 1, còn lại 0. Xuất `data/labels/highlight/{match}.json` (chuỗi nhị phân/giây). Thuật toán DSP cổ điển, không dùng model (@dataset_spec.md 3.4).

---

## 8. `tests/` — tiêu chí pass (khớp @evaluation_plan.md 2.3)

| Test | Nội dung | Tiêu chí pass |
|---|---|---|
| `test_gradient_check.py` | finite-difference vs autograd trên MHA, RMSNorm, SwiGLU (fp64) | `max|Δ| < 1e-4` |
| `test_adamw_parity.py` | AdamW tự viết vs `torch.optim.AdamW`, 100 bước hồi quy nhỏ | `max|w| < 1e-6` |
| `test_overfit_one_batch.py` | mỗi model train 1 batch nhỏ ~200 step | loss ≈ 0 (dưới ngưỡng/model) |
| `test_bpe_roundtrip.py` | encode→decode 10.000 câu | khôi phục 100% |
| `test_sdpa_parity.py` | MHA `use_sdpa=False` vs `True` (self + causal + cross) | `allclose(atol=1e-5)` |
| `test_ctc_parity.py` | `ctc_loss` tự viết vs `torch.nn.CTCLoss` | `allclose(atol=1e-4)` |
| `test_shapes.py` | forward mọi model | shape output đúng bảng model_spec |

Chạy: `python -m pytest ai_core/tests/ -v`. Tất cả pass là điều kiện DoD T1.1.

---

## 9. Checkpoint format & export

**Format thống nhất** (`checkpoint.py`):

```python
ckpt = {
    "config": asdict(model_config),      # tái dựng kiến trúc không cần code ngoài
    "state_dict": model.state_dict(),    # fp32
    "bpe_vocab": {...} | None,           # chỉ Mini-GPT (đính kèm tokenizer để service tự nạp)
    "metrics": {"metric_name": value, "step": int, "seed": int},
}
torch.save(ckpt, "checkpoints/{model}/best.pt")   # + last.pt mỗi epoch
```

**Inference-service nạp** (master plan mục 2.4, `inference-service/`): đọc `best.pt` → `build_model(config)` → `load_state_dict` → `.eval().half().cuda()`. Mini-GPT dựng lại `BPETokenizer` từ `bpe_vocab`. 6 model nạp cùng 1 process (~120MB VRAM fp16), GPU jobs qua asyncio queue tuần tự. Không có logic web trong `ai-core/` — service chỉ import `ai_core` như thư viện.

---

## 10. Task breakdown T1.1–T1.7 (sub-task ≤ 0.5 ngày + DoD)

Khớp master plan mục 3 Phase 1 và lịch @model_spec.md mục 4. GPU tuần tự, xen dev CPU-bound.

### T1.1 (W1) — Primitives + optim + tokenizer + math tests
| Sub | Việc | DoD |
|---|---|---|
| T1.1a | `rmsnorm.py`, `swiglu.py`, `rope.py`, `embedding.py` | forward shape đúng; `swiglu_hidden` bội 64 |
| T1.1b | `attention.py` (softmax tay + SDPA + causal + cross + KVCache) | `test_sdpa_parity` pass |
| T1.1c | `block.py` + init GPT-2 scale | smoke forward self & cross |
| T1.1d | `optim/adamw.py` + `split_decay_params` | `test_adamw_parity` < 1e-6 |
| T1.1e | `tokenizer/bpe.py` + `scripts/train_bpe.py` | `test_bpe_roundtrip` 100%, vocab=8192 |
| T1.1f | `test_gradient_check.py` | `max|Δ| < 1e-4` fp64 |
| T1.1g | `trainer.py`, `schedule.py`, `checkpoint.py`, `config.py` | overfit-1-batch chạy được với 1 model |

### T1.2 (W1–2) — Data pipeline + weak-label
| Sub | Việc | DoD |
|---|---|---|
| T1.2a | Decord trích keyframe 1fps + loại frame đen | manifest JSON/dataset (path, split, checksum) |
| T1.2b | `audio/mel.py` + `features.py` | log-mel 80 khớp công thức; 64-d/giây |
| T1.2c | `scripts/build_weak_labels.py` (cross-correlation) | xuất nhãn nhị phân/giây 50 trận |
| T1.2d | `datasets/*.py` cho ViT, Siamese, ASR | `DataLoader` ra batch đúng shape |
| T1.2e | tool gán nhãn nội bộ (tái dùng heatmap CMS) | gán được category video + vùng highlight |

### T1.3 (W2) — Train ViT + Siamese
| Sub | Việc | DoD |
|---|---|---|
| T1.3a | `vit.py` + `configs/vit.yaml` + train | overfit-1-batch loss≈0; train hội tụ |
| T1.3b | eval ViT + 2 baseline (LogReg histogram, kNN pixel) | Top-1 ≥ 70% (4 lớp MVP) |
| T1.3c | `siamese.py` + `configs/siamese.yaml` + train | Recall@10 ≥ 80% / 1.000 query |
| T1.3d | ablation kiến trúc (PostLN+GELU+PE vs bản dự án) | bảng số liệu (@evaluation_plan 2.2) |
| T1.3e | export `checkpoints/vit/best.pt`, `siamese/best.pt` | service nạp thử OK |

### T1.4 (W3–4) — Train ASR CTC (chạy đêm)
| Sub | Việc | DoD |
|---|---|---|
| T1.4a | `ctc.py` (loss DP + greedy/beam) | `test_ctc_parity` pass |
| T1.4b | `asr_ctc.py` (conv subsample + encoder + head) | overfit-1-batch loss≈0 |
| T1.4c | train VIVOS+CommonVoice + SpecAugment | job train ổn định qua đêm |
| T1.4d | eval WER/CER trên VIVOS test | CER ≤ 20%, WER ≤ 45% (ghi limitation) |
| T1.4e | export `checkpoints/asr_ctc/best.pt` + segments timestamp | service dựng subtitles OK |

### T1.5 (W4) — Train Highlight Fusion + ablation
| Sub | Việc | DoD |
|---|---|---|
| T1.5a | tiền tính ViT embedding/giây (backbone đóng băng) | cache `(n_sec, 256)`/video |
| T1.5b | `highlight_fusion.py` + BCE pos_weight + `configs/*.yaml` | overfit-1-batch loss≈0 |
| T1.5c | train cửa sổ 120s/stride 60s + ghép làm mượt | chuỗi điểm 0–1 cả video |
| T1.5d | eval F1/giây + IoU đoạn trên 5 trận nhãn người | F1 vượt cả 2 baseline ≥ 10 điểm |
| T1.5e | ablation visual-only / audio-only / fusion | bảng chứng minh đa phương thức |

### T1.6 (W5–6) — Pretrain Mini-GPT + fine-tune tóm tắt (chạy đêm)
| Sub | Việc | DoD |
|---|---|---|
| T1.6a | `minigpt.py` + weight tying + KV-cache generate | overfit-1-batch loss≈0; generate chạy |
| T1.6b | `text_dataset.py` + pretrain next-token ≥500MB | perplexity giảm ổn định |
| T1.6c | `summary_dataset.py` + fine-tune (sapo+thân→tiêu đề) | sinh tiêu đề hợp lý |
| T1.6d | eval ROUGE-1/2/L vs Lead-1 | ROUGE-L vượt Lead-1 |
| T1.6e | export `checkpoints/minigpt/best.pt` (kèm `bpe_vocab`) | service map-reduce >1024 token OK |

Follow-up2026-10-19: **aligned summary PREPARATION DONE / HUMAN LABEL AUDIT PENDING**. Candidate984train/64val từeditorial News, giữsplit/hash/exclude frozenIDs, no source/target truncation; sum-aligned-v1 chọn pairedclean/noisy sumROUGE-L, title/cap regression, budget4clean+1noisypasses (248/62steps). 48blankauditrows chưa được xác nhận; trainer chặn trước GPU. Chưa train/deploy/đổi architecture/loss/BPE; News proxy chưa chứng minh real-transcript quality. @docs/T1.6_aligned_summary_preparation.md; fullT1.6 chưa đạt human gate.

Follow-uppreflight2026-10-19 **DATA V2 DONE / HUMAN AUDIT PENDING**: guard cũ chấp nhận teaser../.../…, phát hiện50train+3val; đã sửa sharedfilter+trainer refusal và giữv1 đểđốichiếu. V2=956train/64val (oldsplit preserved/61valretained+3replacements/all53excluded), screening_revision riêng, sameprofile/namespace. 4CPU sanityitems,41tests+4subtests,8160encodedchecks/4productionparity, Go/CMS/Client PASS. Budget240clean/60ASR/eval60; baseline vẫn modelcũ, không improvementclaim. 48annotations v2 vẫntrống; chưa submitcandidate/deploy/fullT1.6 chưađạt. @docs/T1.6_label_preflight.md; @data/manifests/minigpt_label_preflight.json.

### T1.7 (W6) — Train Two-Tower
| Sub | Việc | DoD |
|---|---|---|
| T1.7a | `two_tower.py` + BPR + `movielens_dataset.py` | overfit-1-batch loss≈0 |
| T1.7b | train MovieLens-100k (split thời gian) | hội tụ |
| T1.7c | eval Recall@10, NDCG@10 vs popularity | NDCG@10 vượt popularity |
| T1.7d | export vector 128 L2-norm → Milvus (IP) + `checkpoints/two_tower/best.pt` | recommendation endpoint query OK |

---

## 11. Ghi chú tuân thủ (không vi phạm)

- Không trọng số/tokenizer/pseudo-label pretrained (@dataset_spec.md 0). BPE tự train; nhãn ASR là transcript người tạo; nhãn highlight test là người gán.
- FFT/Mel/cross-correlation/histogram màu là DSP cổ điển (toán, không phải model) — dùng làm feature + baseline.
- AI chỉ ra tensor/float; cắt clip do FFmpeg (@kien_truc 6.3.1) — nằm ngoài `ai-core/`.
- Mọi số liệu luận án lấy từ test set đóng băng, seed cố định, 3 lần lấy mean±std cho thí nghiệm nhỏ (@evaluation_plan 0).

Follow-up 2026-10-19 — **ALIGNED CANDIDATE TRAIN/EVAL DONE; ASR REGRESSION / NOT DEPLOYED**. User confirmed48v2 pairs via chat with exact ID/hash provenance;956train/64val, seed1337,240clean+60ASR,5validation rounds; private Kaggle ai-core-minigpt-aligned-v2 version1 COMPLETE, output downloaded/verified. Predeclared paired-mean selection chose clean180: clean ROUGE-L0.292511→0.517913, synthetic-ASR0.172177→0.114637; noisy repetition/cap hits increased. No quality PASS from mean improvement; fullT1.6 human gate unmet, shared1.6/5 unchanged. T4 allocated1.055/reserved2.520GiB,507.8s baseline+train/validation,4remote sanity+50local tests/4subtests+Go/CMS/Client PASS. Six post-selection video-control outputs still show ASR failure; no new human score. Candidate5cc63c... retained separately, activecf9cfa... unchanged. Report @docs/T1.6_aligned_training.md, curves/metrics/manifests updated. Next: mixed clean+ASR replay and per-condition non-regression guard; reuse unchanged48pair confirmation, no repeated audit. No new experiment launched; Docker engine unavailable/no liveE2E/six-model4GiB proof.

Follow-up 2026-10-19 — **MIXED REPLAY TRAIN/EVAL DONE; SUMMARY GUARD PASS / NOT DEPLOYED**. Same confirmed956/64 and48pair hashes; seed1337, microbatch4clean+4noisy/effective64,300updates/eval60. Private ai-core-minigpt-replay-v1 version1 COMPLETE;4remote sanity+62local Python tests+Go/CMS/Client PASS. Output/rawprediction means/IDs/checkpoint/config/guard/hashes verified. Only mixed300 eligible: clean ROUGE-L0.292511→0.475816, synthetic-ASR0.172177→0.186158, ASR repetition0.174653→0.162928, cap/EOS equal init. Higher-mean240 rejected for ASR repetition. Auxiliary titleRL0.356232→0.343602 regresses, outside summary guard. T4 runtime446.03s, peak allocated1.056/reserved1.805GiB≤8; not inference4GiB proof. Candidate70ec4790... retained separately, activecf9cfa... unchanged; fullT1.6 human gate unmet/shared1.6/5 unchanged. Report @docs/T1.6_mixed_replay.md, metrics/curves/manifest updated. Next: isolated real-ASR paired evaluation then fresh human ratings before promotion; no frozen-test tuning/repeated48pair audit. Docker engine off/no liveHTTP/E2E; no new real-video generation this task.

Follow-up 2026-10-19 — **MIXED CANDIDATE REAL-VIDEO PILOT DONE / ERRORS OBSERVED / NOT DEPLOYED**. User authorized continuation after training. Mixed300 SHA70ec4790... vs activecf9cfa...,3previously inspected clips×3exact inputs (confirmed draft/activeASR/candidateASR)×2models =18fresh nonempty summaries via production helper, CPUFP32/temp0/max96/18.734s. Active cache parity9/9, prior source/service/weights/frozen media/refs/ratings hashes unchanged; no newASR/train/tuning/human score. Still off-topic/repetitive on actualASR; confirmed Newton draft also fails. Summary proxy guard PASS does not establish real-video quality; do not promote, fullT1.6 human gate/shared1.6/5 unchanged. Reviewpacket onD:/data_training_ai/minigpt_news/mixed_replay_video_pilot_3_v1, escaping test+Playwright desktop/mobile3video playback/9pairs/no overflow+visualQC+Go/CMS/Client PASS. @docs/T1.6_mixed_video_pilot.md; @data/manifests/minigpt_mixed_video_pilot.json. Next: separate real-domain human-authored train/validation on new videos outside frozen30/3diagnostics; keep current48News confirmation, no pseudo-labeling of test clips or relaxed guard.

Follow-up 2026-10-19 — **REAL-DOMAIN DATA PREPARATION DONE / HUMAN LABELS0/40 / TRAIN GATE CLOSED**. User requested proposed new data. Downloaded20newCC videos/4new channels outside all10frozen source videos/6test channels, originals499544485bytes retained onD:/data_training_ai/minigpt_domain_v1_20261019. SeededID/channel grouping:15train videos/3channels→30clips;5val videos/1channel→10clips;40×30s=20min.40WAV/MP4 +80own-ASR inputs(active/candidate),0empty/0overbudget/max229prompt tokens, no human/generated-summary targets. Blank authoring page at localhost8890 withJSONexport/autosave, strictID/mediaSHA/attestation/complete-label/budget/disjoint gate; actualblank import rejected/noacceptedexport.20unit tests+Playwright desktop/mobile40cards/4representative playback/UTF8export/autosave/nooverflow+visualQC+Go/CMS/Client PASS. Frozen source/ref/ratings/production weight hashes unchanged; no train/deploy/externalmodel/Kaggleupload; prior48News confirmation retained. Next: humans write these new transcript-summary labels, import/review before bounded training; source-channel split is not verified speaker identity, smallmostly-news domain/near-dups not certified. @docs/T1.6_real_domain_preparation.md; @data/manifests/minigpt_real_domain.json. FullT1.6 human gate/shared1.6/5 unchanged.


- [x] Follow-up 2026-10-19 — **WHISPERWEB CONVERSION DONE, 40/40 DRAFTS; TRAINING NOT STARTED**. User replaced Clideo with WhisperWeb. Public free local browser workflow, whisper-base multilingual/Vietnamese, fixed configuration: 120 TXT/JSON/SRT exports for 40 new 30s clips (30train/10val), kept separately onD:/data_training_ai/minigpt_domain_v1_20261019/whisperweb_drafts_v1. All IDs/output hashes/TXT-JSON agreement,80clip hashes,7prep packet hashes and8frozen/active-weight hashes PASS; collector self-check +Go/CMS/Client checks PASS. 22clips have mechanical review flags (6unknown end,5repeated8word,14outside clip; overlap). External automatic drafts remain unverified, not human labels or summary targets; no gate bypass, train, deploy or weight/test changes. FullT1.6 quality gate/shared1.6/5 unchanged. Next: listen/correct with machine-assisted provenance and author summaries before separate label intake. Report @docs/T1.6_whisperweb_drafts.md; manifests @data/manifests/minigpt_whisperweb_drafts.json and minigpt_whisperweb_verification.json.

- [x] Follow-up 2026-10-20 — WHISPER REVIEW PREPROCESSING DONE. Prepared40editable Whisper transcripts/40blank summaries,22flagged-first, separate browser drafts and assisted-origin export at localhost8890/whisper_review_v1/index.html.21timing proposals across20clips/40derived SRTs; text/raw120exports/original packet/frozen data/weights unchanged.27unit tests, desktop/mobile browser and Go/CMS/Client builds PASS. No API change. Report @docs/T1.6_whisper_review.md; manifest @data/manifests/minigpt_whisper_review.json.
- [ ] Actual listening/corrections and human summaries remain pending: no direct audio-listening tool in this agent session, no invented semantic verification. Await reviewed_whisper_domain_v1.json, then separate intake preserving external-ASR provenance. No training/deploy or T1.6 quality-gate change.


- [x] Follow-up 2026-10-20 — REVIEW JSON RECEIVED AND ERROR AUDIT DONE. Exact73967-byte export SHA860f8068d0bd... saved in whisper_review_v1/received_860f8068d0bd;40IDs/source/media/copy/protected hashes PASS.40transcripts/39edits/37summaries/33feedback/0exported confirmations;31summary copies/25over95BPE/3blank. User error-review pass is received; no invented approval or WER/CER. Separate vocabulary audit: active93 lacksF/J/W/Z,9digits and punctuation; CharVocab silently drops unknown symbols. Candidate133 covers example identifiers but is not promoted. Reviewed page is Whisper-base Transcribe, not a paired project-ASR score or translation test. No code/API/weights/test/train change. Report @docs/T1.6_whisper_review_intake.md; manifest @data/manifests/minigpt_whisper_review_intake.json.
- [ ] Next: fix ASR label unknown-character handling and define English/number/identifier conventions before targeted supervised data and paired ASR evaluation; concise approved summaries are still required for MiniGPT domain training.


- [x] Follow-up 2026-10-20 — T1.4 STRICT LABEL ENCODING/PREFLIGHT DONE. SharedCharVocab rejects unsupported symbols instead of deleting them; alltrain labels validated before audio/model training. SharedReferenceASRDataset/raw-text metrics cover general/robust evaluation without dropping held-out symbols or growing vocabulary. Actual133symbol train13561/13561roundtrip;13557CTCfeasible/4existing exclusions retained;10567legacyVIVOS labels valid.3val/7testOOVlabels preserved; active93mixed training rejected before audio.80Python tests+Go/CMS/Client builds PASS; checkpoints/IDs/head/datasets/frozen tests/review hashes unchanged. Lossless label convention documented in dataset_spec3.3 and @docs/T1.4_asr_label_contract.md; proof @data/manifests/asr_label_preflight.json. No training, promotion, API change or acoustic quality claim.
- [ ] Next safe task: audio-backed supervised domain examples for English/code switching, numeric/legal identifiers, proper names and compounds; approved references and coverage/head checks before a new bounded ASR experiment. Previous40Whisper reviews remain diagnostic/unapproved, not autoaccepted targets.

- [x] Follow-up 2026-10-20 — T1.4 ENGLISH DATA PREPARATION DONE / NOT TRAINED. Downloaded official Mini LibriSpeech archives (459000655bytes), published MD5 and SHA256 verified;2608paired16k mono FLACs decoded/validated onD:/data_training_ai/asr_english_v1_20261020. Train1519/5.310743h/28speakers; dev-clean-2 speaker split seed1337→val580/0.977111h/13speakers +test509/1.058710h/13speakers. All3split speaker/chapter/utterance/audioSHA/exacttext disjoint;1519train labels roundtrip/CTCfeasible,0OOV,133candidate IDs/vocab unchanged.790oldVI train keyword replay matches (notnewlabels/domaingold); selectedacronyms0, code-switch/legal/name gaps remain.12protectedfiles/preparedhashes/actual3splitloader+mel/101Python tests+Go/CMS/Client builds PASS. OriginalVItests/weights/review confirmation state unchanged; noKaggleupload/GPU/train/deploy/EnglishWER/qualityclaim. @docs/T1.4_asr_english_preparation.md; @data/manifests/asr_english_preparation.json. Combinedretainedtrain≈27.32h below30h target; fullAIgate/sharedhuman1.6/5 unchanged. Docker engine unavailable/no liveHTTP/E2E.
- [ ] Next safe task: separate3source VIVOS/FLEURS/MiniLibriSpeech recipe/staging from candidate133, per-domain validation non-regression guards and frozenEnglish/VItest evaluation. Existing2source robusttrainer cannot consume packet unchanged. Domain-specific approved references still needed; do not autoaccept40Whisper reviews or treat pure-English books as verifiedcode-switch/legal coverage.

- [x] Follow-up 2026-10-20 — T1.4 THREE-SOURCE RECIPE/PACKET/STAGING DONE / NOT TRAINED. Sharedrobusttrainer accepts optionalfrozen asr-three-source-v1 (legacy2source unchanged); parentcandidate133 SHAd03ef0..., same133head/architecture/loss,2000updates/seed1337/eval500, sourceprobabilityVIVOS.4/FLEURS.4/English.2 overretainedcounts. Eligiblecheckpoint requires eachdomainWER/CER≤initialbaseline +strictEnglishWER/meanWER improvement; tests runthroughtrainerend prove step0fallback/eligiblebest retention. Test only evaluates afterselection. NewPRIVATEsupplement+kernelmetadata onD:/data_training_ai/asr_three_source_v1_20261020; original2datasets reused.19240audioSHA/fullstaging+9source/splitmel checks,15076retainedtrain/same4exclusions,2034val/2126test, originalVIlabels/splits and3val/7testOOVreference preserved;12protectedhashes PASS.122Python tests includingmathsanity +Go/CMS/Client builds PASS. @docs/T1.4_asr_three_source_preparation.md; @data/manifests/asr_three_source_preparation.json; preflight/staging_check onD:. No upload/remotejob/CUDA/realfinetune/EnglishWER/promotion/liveHTTP. Domain-gold/30htarget/fullAIgate/sharedhuman1.6/5 unchanged; Docker engine unavailable.
- [ ] Next safe task: upload the new private supplement, submit one guarded2000-update Kaggle candidate, then download/verify output and per-domain baseline/validation/test guards. Preserve existing input datasets, activeweights and frozen references; no qualityclaim until actual outputs and independent domain evaluation.

- [x] Follow-up 2026-10-20 — PRIVATE DATASET UPLOAD +SINGLE GPU JOB SUBMITTED. Newasr-three-source-v1 datasetv1 ready/private; oldasr-robust-humanv2/vivos-asrv1 unchanged. Actualcanonical kernel traininghighlight/asr-three-source-guarded-v1 version1; metadata id corrected to APIreturnedslug withoutresubmission. Authoritative pulledmetadata PRIVATE/GPU/InternetOFF/3inputs/sourceparity verified; latestQUEUED, no GPUresult yet.132Python tests+Go/CMS/Client builds PASS. Localbackgroundcollector downloads/validates references/counts/editdistances/metrics/guardedbestselection/weights/hash/8GiB bound/protectedfiles and updatesTodo/plan afterverifiedcompletion; failuresremainpendingdiagnosis. @data/manifests/asr_three_source_training.json; monitor.log onD:/data_training_ai/asr_three_source_v1_20261020. No activeweight/promotion/frozenreference/review change.
- [x] SameGPUjob COMPLETE; collected/verifiedoutputs2026-10-21. No secondrun or guard/test changes. See training/result/real-audio follow-up below.

- [x] T1.4 three-source privateGPU run COMPLETE/output verified:2000updates/seed1337, selected2000, validationrecommendation=True, baselineRetained=False. Fulltest refs/counts/editdistances/metrics/guards/checkpointhash/133vocab/12protectedfiles PASS. No deployment/real-domainqualityclaim; @docs/T1.4_asr_three_source_training.md.

- [x] Follow-up2026-10-21 — T1.4 OUTPUT COLLECTION +REAL-AUDIO PAIRED DIAGNOSTIC DONE / HOLDPROMOTION. LiveKaggleCOMPLETE; resumedstoppedlocalcollector, downloadedoutputs-v1, child05713a... selected2000. MacrotestWER parent→new:VIVOS32.9727→32.5731%,FLEURS53.6727→53.7801%,English113.3507→103.0843%; Englishstillpoor/FLEURSsmallregression preserved. T4training43.21min,peakallocated1.193/reserved3.051GiB<8; fourmathsanityPASS. Independentcollectorrefs/counts/editdistances/guard/beststep/weights/133vocab/protectedhashes verified. Then120freshproductionASR decodes on40oldrealclips/3variants,CPUFP32/35.609s,80/80baselinecacheparity/0empty/validtiming,33feedback/media/reviewstate unchanged; no real-videoWER/goldclaim.139Python tests+Go/CMS/Client builds PASS; plotrendered/inspected. No newGPUjob/promotion/servingweightchange; @docs/T1.4_asr_three_source_real_audio.md; @data/manifests/asr_three_source_real_audio.json. FullAIgate/human1.6/5 unchanged.
- [ ] Next safe task: targeted audio-backed approved ASR references/training for English/code-switch/legal identifiers/numbers/names, preserving the existing review work and provenance. No identicalrecipe rerun or frozen-test tuning; real-word quality remains unresolved.

- [x] Follow-up2026-10-21 — ASR-ONLY REVIEW/INTAKE/SCORER PREPARATION VERIFIED; WORD-LEVEL STATUS PENDING. Oldcheckbox coupledASR+summary and rejectednonemptyfeedback;0oldchecks do not prove0ASRwork. Seeded all40transcripts/39edits/33notes/name,10valfirst+30train unchanged, separateASRattestation/storage, no summaryrequired/no feedbackdeletion. Human-correctedexternalASR origin preserved; strictID/media/source/provenance/speaker guards; scoresnull untilall10fixedvalapproved, then frozenref/cached3modelWER-CER, no testediting or encoderloss. TrainOOVreportedseparately.182tests+browser4viewports/13playbacks/filefallback/200%text/keyboard/nooverflow+visualQC+Go/CMS/Client PASS; originalreview/models/media/frozenfiles unchanged. @docs/T1.4_asr_verbatim_intake.md; @data/manifests/asr_verbatim_preparation.json. Currentactualdedicatedattestations0,noaccepted/frozen/goldfiles/WER/train/promotion; directaudiolisteningtool unavailable.
- [x] Complete actualword-level ASR confirmation/corrections: actual40-approved export received/imported/scored2026-10-21 at14:12 (follow-upbelow).30train/10val done; no approval inferred or hearing fabricated. FullAIgate/human1.6/5 unchanged.

- [x] Follow-up2026-10-21 — ACTUAL ASR EXPORT INTAKE DONE: Downloads asr_verbatim_domain_v1.json50878bytes/SHA009840ca1e6a… archived unchanged. Reviewer khoa minh explicitlyapproved37rows; strictimport exported30/30train+7/10val preservinghuman-reviewedexternalASR provenance/40IDs/media/source/33oldnotes. 3unconfirmedval retainactualspellingfeedback; validation_scores=null/no frozenrefs/no partialdenominator. 2train labels retain? outside133vocab, training_ready=false.16targetedtests/manifestcounts/origins/15protectedhashes/byteparity PASS; data/docs-only, no appbuildrerun/code/model/vocab/test/summary/train/deploy change. @docs/T1.4_asr_verbatim_results.md; @data/manifests/asr_verbatim_intake.json.
- [x] Remaininglabelcompletion resolved by actualnewexport SHAa1ecca1bc0cd…:3formerlypendingval explicitlyconfirmed,2textsupdated; fixed10/3checkpointscored. Train-only?coverage/headpreflight preparedseparately134,nottrained; no autoapproval/characterdeletion/promotion. FullAIgate/human1.6/5 unchanged.

- [x] Follow-up2026-10-21 — DOMAIN TRAIN-ONLY PREFLIGHT VERIFIED / THREE VALIDATION ATTESTATIONS PENDING. Saved2textspellingproposals/3clips separately withfalseconfirmation/non-goldprotocol; thirdclipalreadycontainsnotedcorrections, noinventedhearing/guessingambiguousApplephrase. Candidatevocab134 appends? solelyfrom2approvedtrainlabels,133oldIDs unchanged;30labelsstrictloader/roundtrip/30actualaudiohash16kmono/CTCfeasibility PASS,total0.25h. Existingexpand_head verifiedalloldweights/133headrowsexactinCPURAM, newrowuntrained/nocheckpointwrite/nosoftmaxparityclaim.39tests+15protectedhashes PASS; originalintake30/7/scoresnull/weights/tests/productionvocab unchanged. No appcode/buildrerun/train/remotejob/promotion. @docs/T1.4_asr_domain_followup.md; @data/manifests/asr_domain_followup_preflight.json. Missing3audio-backedreferences requested fromuser; fullAIgate/human1.6/5 unchanged.

- [x] Follow-up2026-10-21 — ASR CONFIRMATION ERROR UX FIX DONE. Nonemptyexclude_reason correctlyblocked3pendingclips, genericmessage replacedwith4specificcauses/invalidfieldfocus/aria-invalid; noautoclear/approval. Browserregression FAILbefore/PASSafter,4viewports13playbacks+desktop/mobile37confirmationresume+visualQC PASS. Python16/Go vet-test-build/CMS tsc-Vite/Client tsc-Next full lint14pages PASS;15protectedhashes/packet/localStoragekey/importerguard unchanged. ServedHTMLupdated/oldHTMLarchived; @docs/T1.4_asr_verbatim_intake.md. Actual3audioattestations/10valscore/train stillpending, fullAIgate unchanged.

- [x] Follow-up2026-10-21 — ACTUAL40ATTESTATIONS IMPORTED / FIXED10 SCORED+FROZEN / HOLDPROMOTION. NewDownloads50690bytes/SHAa1ecca1bc0cd… archivedexact,40true/noexclude/30train10val; trainitemsunchanged,2valtextsupdated. MacroWER/CER% active96.1333/55.8295,parent91.6021/47.4726,three_source94.5083/49.3379; childWER+2.9061ppvsparent, allreal-domainqualitypoor. Cachedmedia/checkpointbinding+independentfull-matrix editdistance all30predictions/macro/corpus/errorcounts+frozen10/snapshot/15protectedhashes PASS;16targetedtests PASS. No codechange/appbuildrepeat/train/deploy/summarytarget; current133training_readyfalsebecause? while134train-onlypreflight stillapplies. @docs/T1.4_asr_verbatim_results.md; @data/manifests/asr_verbatim_intake.json. No further3clipconfirmationneeded; fullAIgate/human1.6/5 unchanged.
- [x] Bounded domain-adaptation recipe/packet fromparent133 withtrain-only134/domain30train+oldVI/ENreplay prepared2026-10-21; fixed10/originaltests preserved. Detailsbelow; no training/promotion.

- [x] Follow-up2026-10-21 — DOMAIN REPLAY RECIPE/PACKET/LOCAL PREFLIGHT DONE, NOT TRAINED. Parentd03ef0…→134onlyappend?,500updates/seed1337/eval100/LR3e-5/batch4×4, sourceprobabilitiesVIVOS.4/FLEURS.3/EN.2/domain.1. All4WER/CERnonregression+strictdomainWER/CER+meanWERimprovement; original133fallback andselectedvocabcorrect ifnoeligible, notuntrained134. Sharedtrainer/wrapper preservelegacy2/3source.157tests incl13newdomain/actualdriverCPU-stubaccept-reject +Go/CMS/Client fullchecks PASS. Actual19280audioSHA/40domainZIP/15110rawtrainroundtrip/15106retained/same4CTCexclusions/11Mel loaders/sampling/frozen10/codebundle/actualparentheadprefix PASS; protectedfiles unchanged. Canonicalreferenceidentity separatefrombytehash forCRLF/LF, frozenbytesunchanged. Newprivatepacket+runner onD:/data_training_ai/asr_domain_replay_v1_20261021, @docs/T1.4_asr_domain_replay_preparation.md, @data/manifests/asr_domain_replay_preparation.json. No remoteupload/job/quality/VRAM/deploy claim; Dockerengineoff/fullAIgate/human1.6/5 unchanged.
- [x] Newprivateasr-domain-replay-v1supplement v1 uploaded/ready; exactlyoneguarded500-updateKagglejobv1 submitted2026-10-21. Authoritative pulledmetadata private/GPU/InternetOFF/T4/4inputs/runnerparity verified; liveRUNNING. Previous3privateinputversions1/2/1 andoldjobs verified; no overwrite. @docs/T1.4_asr_domain_replay_training.md; @data/manifests/asr_domain_replay_training.json.
- [x] Current500-updatev1run COMPLETE/output verified2026-10-22. All5updates fail replayguard; selectedstep0/original133retained, recommendationfalse. Domainfull30sWER91.2610→best83.8031at400 butVIVOSWER+0.1232pp/FLEURSWER+2.2180pp; no neweligiblemodel. Both2126-testreference/prediction/editdistance/aggregate checks,133config/vocab/tensorfallback/4sanitylogs/22protectedhashes PASS. T4train+eval18.0942min,peak1.1166/2.5039GiB<8 (notinferenceproof). CollectorJSONeventdecodefix catchesescaped\\u003c;180tests+Go/CMS/Clientfullchecks PASS,noGPUrerun. Plotrendered/inspected; @docs/T1.4_asr_domain_replay_training.md, @data/manifests/asr_domain_replay_training.json. Activeweights/frozenrefs/ratings unchanged, fullAIgate/human1.6/5 unchanged; HOLDPROMOTION.
- [x] Train-only error/coverage audit DONE 2026-10-22:30 approved train/15min/3channels; parent133 WER/CER91,5664%/48,5375%, rejectedlast13479,5772%/38,9247% (in-sample only). English cues ONLINE×3/CPI×1; structured legal IDs regex0; no generalization/promotion claim. New supplement:9 public CC sources/9 new channels outside all previous channels,60×20s=20min, raw sources/provenance/WAV/MP4 on D:/data_training_ai/asr_domain_expansion_v2_20261022. 0 new labels, training_ready=false, blank loader rejection PASS. Independent media/hash/PCM checks +9 playback +194 tests +Go/CMS/Client builds PASS; protected refs/weights unchanged. @docs/T1.4_asr_train_error_audit.md; @data/manifests/asr_domain_expansion_v2.json. No training/upload/deploy; HOLD PROMOTION.
- [ ] Next safe task: draft transcription then human word-level review of NEW60 clips; verify actual English/code-switch/identifier/number/name coverage and retain machine-assisted provenance. After approved labels, perform train-only vocabulary/CTC checks before a separate guarded training recipe. Do not request old40 re-review, rerun identical job, relax guard, tune on test, or deploy rejectedlast.pt. Pilot20min not sufficient evidence of full coverage.

- [x] Historical file-access blocker resolved by user; draft conversion/review preparation now DONE (follow-up below). Previous status:NEW60 draft transcription:WAITING_CHROME_LOCAL_FILE_ACCESS. Chrome browser tool blocked firstWAV because ChatGPT extension needs Allow access to file URLs; user notified, no permission changed/no bypass. WhisperWeb local UI selected base291MB/Multilingual/AutoDetect/Transcribe/unquantized. Actual transcripts0/60, human approvals0, no actual reviewpage. Reused ASR-only review generator/newprotocol/storage/export +WAV/language guard;8newtests,104relatedtests/Go/CMS/Client builds PASS; isolated60card TEST_ONLY mobile390/desktop1440/guard/export fixture QA only. New120media/9source/protectedhashes unchanged. @docs/T1.4_asr_expansion_transcription.md; @data/manifests/asr_expansion_transcription.json. Resume file selection/conversion after user enablespermission; no training/promotion/old40re-review.

- [x] 2026-10-22 — NEW60 DRAFTS +ACTUAL REVIEW PAGE DONE / HUMAN REVIEW PENDING. FinalWhisperWeblocalbase291MB/unquantized/Multilingual/Transcribe,6English+54Vietnameseexplicitsettings verified perjob; AutoDetect8/pilots retainedseparate afterrepetition diagnosis.180rawfiles81,057bytes/60receipts/TXT-JSON/source/hash PASS.25flaggedclips (14outside8null3short3repeat),2groups9duplicatedrafttexts; notgold/hearing/coverageproof. Actualreview60cards/0approvals/blankname/language/WAV+MP4/assistedorigin/export60unverified PASS; desktop1440/mobile390/visualQC/padding12px/playback PASS.104Python+JSchecks+Go/CMS/Client finalbuilds PASS;120media/9source/25protectedhashes unchanged. Page http://127.0.0.1:8891/asr_review_v2/index.html (loopbackPID16000); @docs/T1.4_asr_expansion_transcription.md, @data/manifests/asr_expansion_transcription.json. No training/deployment/testtuning/guardrelaxation; HOLDPROMOTION.
- [ ] Next:human word-level review/correction or explicit exclusion of NEW60, prioritizing9duplicate+25flagged; exportactualasr_expansion_review_v2.json, then separate strictintake preservingmachine-assistedorigin +coverage/train-onlyvocab/CTC/splitchecks before anynewrecipe. Do not ask old40 to be reapproved or deployrejectedlast134.
