"""Train one of the six models from a YAML config.

The data arguments deliberately stay file-based so experiments are reproducible and
the trainer does not depend on a database or web service.
"""

import argparse
import json
import math
import os

import torch
from torch.utils.data import DataLoader

from ..config import load_configs
from ..training import Trainer
from ..training.datasets import (
    ASRDataset,
    BPRTripleDataset,
    CharVocab,
    HighlightWindowDataset,
    SiamesePairDataset,
    SummaryPairDataset,
    TextChunkDataset,
    TokenFileDataset,
    ViTKeyframeDataset,
    collate_ctc,
    vit_augment,
    load_movielens_ratings,
    time_split,
)
from ..training.loss_fns import LOSS_FNS
from .evaluate import accuracy, f1_per_second, ndcg_at_k, recall_at_k, wer


def _read_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _pad_lm(batch):
    """Pad summary examples; text chunks are already fixed length."""
    max_len = max(x.shape[0] for x, _ in batch)
    xs, ys = [], []
    for x, y in batch:
        pad = max_len - x.shape[0]
        xs.append(torch.cat([x, torch.zeros(pad, dtype=x.dtype)]))
        ys.append(torch.cat([y, torch.full((pad,), -100, dtype=y.dtype)]))
    return torch.stack(xs), torch.stack(ys)


def _summary_metric(model, loader, device):
    # Training loss is the only deterministic metric available without adding
    # a second generation pass; ROUGE is computed by the standalone evaluator.
    total, count = 0.0, 0
    for x, y in loader:
        logits, _ = model(x.to(device))
        total += torch.nn.functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]), y.to(device).reshape(-1), ignore_index=-100
        ).item()
        count += 1
    return total / max(1, count)


def _ppl_metric(max_batches: int):
    """Perplexity = exp(CE trung bình theo TOKEN) trên val — DoD T1.6b "perplexity giảm ổn định".

    Trung bình theo token chứ không theo batch (như `_summary_metric`): chunk pretrain dài bằng
    nhau nên hai cách trùng nhau ở đây, nhưng theo token mới đúng định nghĩa khi batch cuối lẻ.
    Chỉ chấm `max_batches` batch đầu (cố định, không xáo): chấm cả val mỗi lần eval là vài phút
    GPU, còn đường cong vẫn so được giữa các step vì luôn là cùng các chunk đó.
    """
    def metric(model, loader, device):
        total, count = 0.0, 0
        for b, (x, y) in enumerate(loader):
            if b >= max_batches:
                break
            logits, _ = model(x.to(device))                  # fp32: 100 batch vẫn nhanh, số chính xác hơn
            y = y.to(device)
            total += torch.nn.functional.cross_entropy(
                logits.float().reshape(-1, logits.shape[-1]), y.reshape(-1), reduction="sum").item()
            count += y.numel()
        return math.exp(total / max(1, count))
    return metric


def _vit_metric(model, loader, device):
    values = []
    for x, y in loader:
        values.append(accuracy(model(x.to(device)), y.to(device)))
    return sum(values) / max(1, len(values))


def _highlight_metric(model, loader, device):
    scores, labels = [], []
    for vision, audio, target in loader:
        scores.append(model(vision.to(device), audio.to(device)).detach().cpu())
        labels.append(target)
    return f1_per_second(torch.cat(scores), torch.cat(labels))


def _asr_metric(vocab):
    from ..models.ctc import ctc_greedy_decode

    def metric(model, loader, device):
        values = []
        for mel, mel_len, targets, target_len in loader:
            log_probs, out_len = model(mel.to(device), mel_len.to(device))
            predicted = ctc_greedy_decode(log_probs.float().cpu(), out_len.cpu())
            for index, ids in enumerate(predicted):
                expected = targets[index, :target_len[index]].tolist()
                values.append(wer(vocab.decode(expected), vocab.decode(ids)))
        return sum(values) / max(1, len(values))

    return metric


def _siamese_metric(model, loader, device):
    embeddings_a, embeddings_b = [], []
    for a, b in loader:
        embeddings_a.append(model.encode(a.to(device)).cpu())
        embeddings_b.append(model.encode(b.to(device)).cpu())
    if not embeddings_a:
        return 0.0
    a = torch.cat(embeddings_a)
    b = torch.cat(embeddings_b)
    ranked = (a @ b.T).topk(min(10, b.shape[0]), dim=1).indices.tolist()
    relevant = [{i} for i in range(b.shape[0])]
    return recall_at_k(ranked, relevant, min(10, b.shape[0]))


def _two_tower_metric(model, loader, device):
    # The validation loader is built from triples; each row's positive item is relevant.
    ranked_ids, relevant = [], []
    users, positives = [], []
    for batch in loader:
        user, positive = batch[0], batch[1]      # batch có thể là 3 hoặc 5 phần tử (logQ)
        users.append(user.to(device))
        positives.append(positive.to(device))
    if not users:
        return 0.0
    user = torch.cat(users)
    positive = torch.cat(positives)
    user_vectors = model.user_embed(user)
    item_vectors = model.video_embed(positive)
    scores = user_vectors @ item_vectors.T
    ranked_ids = scores.argsort(dim=1, descending=True).cpu().tolist()
    relevant = [{i} for i in range(item_vectors.shape[0])]
    return ndcg_at_k(ranked_ids, relevant, 10)


def _build_loaders(model_name: str, model_cfg, train_cfg, args):
    """Dựng (train_loader, val_loader) theo model. Import dataset lazy để tránh phụ thuộc thừa."""
    if model_name == "vit":
        if not args.manifest:
            raise SystemExit("vit cần --manifest FILE")
        # Augment CHỈ cho train (model_spec §2); val/test giữ ảnh gốc để metric không dao động.
        tr = ViTKeyframeDataset(args.manifest, "train", model_cfg.img_size, augment=vit_augment)
        va = ViTKeyframeDataset(args.manifest, "val", model_cfg.img_size)
        # Giải mã JPEG + augment trên CPU là nút cổ chai (GPU chỉ ~5M tham số); không có worker thì
        # GPU ngồi chờ phần lớn thời gian. persistent: Trainer lặp loader vô hạn (xem nhánh minigpt).
        return (DataLoader(tr, batch_size=train_cfg.batch_size, shuffle=True, drop_last=True,
                           num_workers=args.workers, persistent_workers=args.workers > 0),
                DataLoader(va, batch_size=train_cfg.batch_size, num_workers=args.workers),
                {"classes": sorted(tr.class_to_idx, key=tr.class_to_idx.get)}, _vit_metric)
    if model_name == "siamese":
        if not args.manifest:
            raise SystemExit("siamese cần --manifest FILE")
        tr = SiamesePairDataset(args.manifest, "train", model_cfg.img_size)
        va = SiamesePairDataset(args.manifest, "val", model_cfg.img_size)
        return (DataLoader(tr, batch_size=train_cfg.batch_size, shuffle=True, drop_last=True),
                DataLoader(va, batch_size=train_cfg.batch_size), {}, _siamese_metric)
    if model_name == "asr_ctc":
        if not args.manifest or not args.vocab:
            raise SystemExit("asr_ctc cần --manifest FILE và --vocab FILE")
        raw_vocab = _read_json(args.vocab)
        chars = raw_vocab.get("chars", raw_vocab) if isinstance(raw_vocab, dict) else raw_vocab
        vocab = CharVocab(chars)
        model_cfg.n_chars = vocab.size
        # SpecAugment CHỈ cho train (T1.4c). Bật cho val thì số đo dao động theo may rủi từng lần
        # chạy và early-stop chọn checkpoint theo nhiễu.
        tr = ASRDataset(args.manifest, "train", vocab, n_mels=model_cfg.n_mels, augment=True)
        va = ASRDataset(args.manifest, "val", vocab, n_mels=model_cfg.n_mels)
        return (DataLoader(tr, batch_size=train_cfg.batch_size, shuffle=True, collate_fn=collate_ctc),
                DataLoader(va, batch_size=train_cfg.batch_size, collate_fn=collate_ctc),
                {"char_vocab": vocab.itos}, _asr_metric(vocab))
    if model_name == "highlight_fusion":
        if not args.features:
            raise SystemExit("highlight_fusion cần --features FILE (.pt: {train:[...], val:[...]})")
        raw = torch.load(args.features, map_location="cpu", weights_only=False)
        if not raw.get("train"):
            raise SystemExit("highlight_fusion không có train samples")
        tr = HighlightWindowDataset(raw["train"], model_cfg.window_seconds, model_cfg.window_seconds // 2)
        va = HighlightWindowDataset(raw.get("val", raw["train"]), model_cfg.window_seconds, model_cfg.window_seconds // 2)
        return (DataLoader(tr, batch_size=train_cfg.batch_size, shuffle=True),
                DataLoader(va, batch_size=train_cfg.batch_size) if len(va) else None,
                {}, _highlight_metric if len(va) else None)
    if model_name == "minigpt":
        if not args.vocab or (not args.corpus and not args.summary_json and not args.tokens):
            raise SystemExit("minigpt cần --vocab FILE và --tokens DIR / --corpus GLOB... / --summary-json FILE")
        from ..tokenizer import BPETokenizer
        tokenizer = BPETokenizer.load(args.vocab)
        model_cfg.vocab_size = max(model_cfg.vocab_size, tokenizer.vocab_size)
        if args.tokens:
            meta = _read_json(os.path.join(args.tokens, "meta.json"))
            if meta["vocab_size"] != tokenizer.vocab_size:
                # token encode bằng BPE khác → id trỏ sai chữ, loss vẫn giảm, không có gì báo
                raise SystemExit(f"tokens encode với vocab {meta['vocab_size']}, --vocab là "
                                 f"{tokenizer.vocab_size} — sai cặp file")
            tr = TokenFileDataset(os.path.join(args.tokens, "train.bin"), model_cfg.context_len)
            va = TokenFileDataset(os.path.join(args.tokens, "val.bin"), model_cfg.context_len)
            if not len(tr) or not len(va):
                raise SystemExit(f"tokens rỗng: train {len(tr)} / val {len(va)} chunk")
            # persistent_workers: Trainer lặp loader vô hạn (_cycle); không giữ worker thì mỗi vòng
            # dữ liệu tạo lại 2 process — trên Windows (spawn) là vài giây import torch mỗi lần.
            return (DataLoader(tr, batch_size=train_cfg.batch_size, shuffle=True, drop_last=True,
                               num_workers=2, pin_memory=True, persistent_workers=True),
                    DataLoader(va, batch_size=train_cfg.batch_size),
                    {"bpe_vocab": _read_json(args.vocab)}, _ppl_metric(args.val_batches))
        if args.summary_json:
            pairs = [tuple(item) for item in _read_json(args.summary_json)]
            ds = SummaryPairDataset(pairs, tokenizer, context_len=model_cfg.context_len)
        else:
            ds = TextChunkDataset(args.corpus, tokenizer, model_cfg.context_len)
        if not len(ds):
            raise SystemExit("minigpt dataset rỗng: kiểm tra corpus/summary JSON")
        loader = DataLoader(ds, batch_size=train_cfg.batch_size, shuffle=True, collate_fn=_pad_lm)
        return loader, None, {"bpe_vocab": _read_json(args.vocab)}, None
    if model_name == "two_tower":
        if not args.ratings or not args.user_features or not args.video_features:
            raise SystemExit("two_tower cần --ratings FILE --user-features FILE --video-features FILE")
        train_ratings, val_ratings = time_split(load_movielens_ratings(args.ratings))
        users = {int(k): torch.tensor(v, dtype=torch.float32) for k, v in _read_json(args.user_features).items()}
        videos = {int(k): torch.tensor(v, dtype=torch.float32) for k, v in _read_json(args.video_features).items()}
        if not train_ratings:
            raise SystemExit("two_tower không có rating dương trong train split")
        model_cfg.user_dim = next(iter(users.values())).numel()
        model_cfg.video_dim = next(iter(videos.values())).numel()
        missing = {item for item in train_ratings + val_ratings if item[0] not in users or item[1] not in videos}
        if missing:
            raise SystemExit(f"two_tower thiếu feature cho {len(missing)} rating")
        train_ds = BPRTripleDataset(train_ratings, users, videos, len(videos), train_cfg.seed,
                                    neg_alpha=train_cfg.neg_alpha)
        val_ds = BPRTripleDataset(val_ratings or train_ratings, users, videos, len(videos), train_cfg.seed,
                                  neg_alpha=train_cfg.neg_alpha)
        return (DataLoader(train_ds, batch_size=train_cfg.batch_size, shuffle=True),
                DataLoader(val_ds, batch_size=train_cfg.batch_size), {}, _two_tower_metric)
    raise SystemExit(f"Không có loader cho model '{model_name}'")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--manifest", help="manifest dataset")
    ap.add_argument("--vocab", help="char vocab JSON (asr)")
    ap.add_argument("--corpus", nargs="*", help="text glob(s) cho minigpt pretrain")
    ap.add_argument("--summary-json", help="JSON [[transcript, summary], ...] cho minigpt fine-tune")
    ap.add_argument("--tokens", help="thư mục train.bin/val.bin/meta.json của tokenize_corpus (minigpt pretrain)")
    ap.add_argument("--workers", type=int, default=0, help="DataLoader workers (vit)")
    ap.add_argument("--val-batches", type=int, default=100, help="số batch val mỗi lần chấm perplexity")
    ap.add_argument("--features", help="torch file cho highlight features")
    ap.add_argument("--ratings", help="MovieLens u.data")
    ap.add_argument("--user-features", help="JSON user_id -> feature list")
    ap.add_argument("--video-features", help="JSON video_id -> feature list")
    args = ap.parse_args()

    model_cfg, train_cfg = load_configs(args.config)
    from .. import build_model
    train_loader, val_loader, metadata, metric = _build_loaders(model_cfg.name, model_cfg, train_cfg, args)
    model = build_model(model_cfg.name, model_cfg)
    if train_cfg.eval_every == 0 and metric is not None:
        train_cfg.eval_every = 100

    trainer = Trainer(
        model, train_loader, val_loader, train_cfg,
        loss_fn=LOSS_FNS[train_cfg.loss or model_cfg.name], model_cfg=model_cfg,
        bpe_vocab=metadata.pop("bpe_vocab", None), metadata=metadata,
        compute_metric=metric,
    )
    metrics = trainer.train()
    print(f"Done {model_cfg.name}: {metrics}")


if __name__ == "__main__":
    main()
