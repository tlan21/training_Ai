# ai-core

Thuật toán AI nguyên thủy **tự code 100%** cho hệ thống phân tích video & highlight (luận án). Chỉ dùng PyTorch làm nền tensor + autograd — attention, RMSNorm, SwiGLU, RoPE, AdamW, BPE, FFT/Mel, CTC đều tự cài. **Cấm pretrained/tokenizer ngoài/pseudo-label** (dataset_spec §0).

## Cài đặt

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/Scripts/python.exe torch numpy pyyaml pytest tensorboard
# dữ liệu (T1.2+): uv pip install soundfile decord
```

## Trạng thái (khớp .claude/plan/01_ai_core_plan.md)

| Task | Nội dung | Trạng thái |
|---|---|---|
| T1.1 | primitives + optim + tokenizer + math tests | ✅ code + test pass |
| T1.2b | audio mel + features | ✅ code + test pass |
| T1.4a | CTC loss/decode + parity | ✅ code + test pass |
| Kiến trúc 6 model | vit/siamese/asr/fusion/minigpt/two_tower | ✅ code + shape/overfit test pass |
| T1.2a,c,d | keyframe/manifest, shot boundary, weak-label, 7 loader, train/eval entrypoint | ✅ code + logic test pass (chạy khi có dữ liệu) |
| T1.2e | tool gán nhãn web nội bộ | ⏳ (thuộc CMS) |
| T1.3–T1.7 | train + đạt metric ngưỡng | ⏳ cần dữ liệu thật + GPU CUDA |
| T1.8 | inference-service :8001 | ⏳ sau khi có checkpoint |

## Test toán học (điều kiện DoD T1.1)

```bash
cd ai-core
../.venv/Scripts/python.exe -m pytest ai_core/tests/ -v
```

Bao gồm: gradient check (<1e-4), AdamW parity (<1e-6), SDPA parity, CTC parity (vs `torch.nn.CTCLoss`), BPE roundtrip (100%), overfit-1-batch cả 6 model.

## T1.2 data pipeline

```bash
python -m ai_core.scripts.prepare_keyframes --videos ../data/raw/videos --labels ../data/labels/categories.json --out ../data/processed/keyframes --manifest ../data/manifests/vit.json
python -m ai_core.scripts.build_asr_manifest --audio ../data/raw/asr --transcripts ../data/raw/asr/transcripts.json --manifest ../data/manifests/asr.json
python -m ai_core.scripts.build_asr_vocab --manifest ../data/manifests/asr.json --out ../data/manifests/asr_vocab.json
python -m ai_core.scripts.build_weak_labels --full ../data/raw/matches --highlight ../data/raw/highlights --out ../data/labels/highlight
```

The highlight pipeline is intentionally two-stage: train ViT first, extract one
embedding per second, then combine it with `audio_features_per_second` and the
weak labels.

## Train / eval 1 model

```bash
../.venv/Scripts/python.exe -m ai_core.scripts.train_bpe --corpus data/text/*.txt --out data/manifests/bpe_vocab.json
../.venv/Scripts/python.exe -m ai_core.scripts.train --config ai_core/training/configs/vit.yaml --manifest ../data/manifests/vit.json
../.venv/Scripts/python.exe -m ai_core.scripts.train --config ai_core/training/configs/siamese.yaml --manifest ../data/manifests/vit.json
../.venv/Scripts/python.exe -m ai_core.scripts.train --config ai_core/training/configs/asr_ctc.yaml --manifest ../data/manifests/asr.json --vocab ../data/manifests/asr_vocab.json

# T1.5: extract ViT embeddings, then build aligned fusion tensors
../.venv/Scripts/python.exe -m ai_core.scripts.extract_vit_embeddings --checkpoint checkpoints/vit/best.pt --manifest ../data/manifests/vit.json --out ../data/processed/vit_embeddings.pt
../.venv/Scripts/python.exe -m ai_core.scripts.build_highlight_features --audio ../data/raw/matches --vision ../data/processed/vit_embeddings.pt --labels ../data/labels/highlight --manifest ../data/manifests/vit.json --out ../data/processed/highlight_features.pt
../.venv/Scripts/python.exe -m ai_core.scripts.train --config ai_core/training/configs/highlight_fusion.yaml --features ../data/processed/highlight_features.pt

# T1.6: pretrain uses --corpus; fine-tune uses --summary-json
../.venv/Scripts/python.exe -m ai_core.scripts.train --config ai_core/training/configs/minigpt_pretrain.yaml --vocab ../data/manifests/bpe_vocab.json --corpus ../data/text/*.txt
../.venv/Scripts/python.exe -m ai_core.scripts.train --config ai_core/training/configs/minigpt_finetune_summary.yaml --vocab ../data/manifests/bpe_vocab.json --summary-json ../data/raw/summaries.json

# T1.7: feature JSON maps numeric IDs to fixed-length vectors
../.venv/Scripts/python.exe -m ai_core.scripts.train --config ai_core/training/configs/two_tower.yaml --ratings ../data/raw/movielens/u.data --user-features ../data/processed/user_features.json --video-features ../data/processed/video_features.json

../.venv/Scripts/python.exe -m ai_core.scripts.validate_artifacts --checkpoints checkpoints
```

Checkpoint xuất `checkpoints/{model}/{best,last}.pt` theo format §9 để `inference-service/` nạp.

## Cấu trúc

- `primitives/` — MHA (softmax tay + SDPA), RMSNorm, SwiGLU, RoPE, TransformerBlock, embedding
- `optim/adamw.py` — AdamW tự viết + tách nhóm weight-decay
- `tokenizer/bpe.py` — BPE byte-level vocab 8192
- `audio/` — STFT + Mel filterbank 80 + SpecAugment + features 64-d/giây
- `vision/patchify.py` — patch embed ViT
- `models/` — 6 model + `ctc.py`
- `training/` — Trainer (bf16, grad-accum, clip, ckpt, TensorBoard) + schedule + checkpoint + configs
- `tests/` — kiểm chứng toán học
