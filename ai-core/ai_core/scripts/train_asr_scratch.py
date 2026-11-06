"""AI-29: train a larger CTC ASR FROM SCRATCH on the union of the project's admissible data (no initial checkpoint).

Reuses the robust-ASR dataset, weighted multi-source sampler and evaluator of finetune_asr_robust. Selection = mean WER over the
Vietnamese validation sources (vivos, fleurs, fosd, commonvoice, domain); MiniLibriSpeech is evaluated but not selected on.
Test sets are never touched here.

  python -m ai_core.scripts.train_asr_scratch --manifest M --vocab V --output O --steps 12000 [--init last.pt]
"""
import argparse
import collections
import json
from dataclasses import replace
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset, WeightedRandomSampler

from .. import build_model
from ..config import TrainConfig, load_configs
from ..training.checkpoint import load_checkpoint
from ..training.datasets import CharVocab, ReferenceASRDataset, collate_ctc, collate_references
from ..training.loss_fns import asr_loss
from ..training.trainer import Trainer, set_seed
from .finetune_asr_robust import RobustASRDataset, evaluate, sampling_weights

PROBABILITIES = {'vivos': .25, 'fleurs': .15, 'minilibrispeech': .05, 'real_domain_user_review': .15, 'fosd': .3, 'commonvoice': .1}
SELECT = ('vivos', 'fleurs', 'real_domain_user_review', 'fosd', 'commonvoice')
VAL_CAP = 300  # per source, first-N in manifest order, to bound evaluation time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True, type=Path)
    p.add_argument('--vocab', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--steps', type=int, default=12000)
    p.add_argument('--eval-every', type=int, default=2000)
    p.add_argument('--d-model', type=int, default=384)
    p.add_argument('--layers', type=int, default=12)
    p.add_argument('--heads', type=int, default=6)
    p.add_argument('--lr', type=float, default=5e-4)
    p.add_argument('--init', type=Path, help='continue from a previous session (weights only; new LR schedule)')
    args = p.parse_args()
    assert torch.cuda.is_available(), 'real training requires CUDA'
    set_seed(1337)
    torch.set_num_threads(2)
    args.output.mkdir(parents=True, exist_ok=True)
    vocab = CharVocab(json.loads(args.vocab.read_text(encoding='utf-8'))['chars'])
    base_model, _ = load_configs(str(Path(__file__).parents[1] / 'training/configs/asr_ctc.yaml'))
    cfg = replace(base_model, d_model=args.d_model, n_layers=args.layers, n_heads=args.heads, n_chars=vocab.size)
    model = build_model('asr_ctc', cfg)
    if args.init:
        saved = load_checkpoint(str(args.init))
        assert (saved.get('char_vocab') or saved['metadata']['char_vocab']) == vocab.itos and saved['config']['d_model'] == args.d_model
        model.load_state_dict(saved['state_dict'])
    params = sum(t.numel() for t in model.parameters())
    train = RobustASRDataset(str(args.manifest), 'train', vocab, augment=True)
    val = ReferenceASRDataset(str(args.manifest), 'val', vocab)
    sources = sorted(PROBABILITIES)
    val_loaders = {s: DataLoader(Subset(val, [i for i, it in enumerate(val.items) if it.extra['source'] == s][:VAL_CAP]),
                                 batch_size=1, num_workers=2, collate_fn=collate_references) for s in sources}
    weights = sampling_weights(train.items, PROBABILITIES)
    sampler = WeightedRandomSampler(weights, len(train), replacement=True, generator=torch.Generator().manual_seed(1337))
    loader = DataLoader(train, batch_size=8, sampler=sampler, num_workers=2, persistent_workers=True, pin_memory=True,
                        drop_last=True, collate_fn=collate_ctc)
    precision = torch.bfloat16 if torch.cuda.is_bf16_supported(including_emulation=False) else torch.float16
    device = torch.device('cuda')
    history = []

    def metric(network, loaders, _device):
        domains = {s: {k: v for k, v in evaluate(network, data, vocab, device, precision).items() if k != 'predictions'}
                   for s, data in loaders.items()}
        value = sum(domains[s]['wer'] for s in SELECT) / len(SELECT)
        history.append({'eval': len(history) + 1, 'selection_wer': value, 'domains': domains})
        (args.output / 'history.json').write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding='utf-8')
        print('validation', json.dumps({'selection_wer': round(value, 4), **{s: (round(d['wer'], 4), round(d['cer'], 4)) for s, d in domains.items()}}), flush=True)
        network.train()
        return value

    tcfg = TrainConfig(model='asr_ctc', lr=args.lr, weight_decay=.01, batch_size=8, grad_accum=2, max_steps=args.steps, warmup_ratio=.05,
                       precision='bf16' if precision == torch.bfloat16 else 'fp16', seed=1337, eval_every=args.eval_every,
                       metric_name='wer', ckpt_dir=str(args.output), log_dir=str(args.output / 'runs'))
    metadata = {'char_vocab': vocab.itos, 'task': 'AI-29 scratch ASR', 'params': params, 'sampling_probabilities': PROBABILITIES,
                'selection': 'mean val WER over ' + ','.join(SELECT), 'init': str(args.init) if args.init else None,
                'training_counts': dict(collections.Counter(i.extra['source'] for i in train.items)), 'training_exclusions': len(train.excluded)}
    print('MODEL', json.dumps({'params': params, 'd_model': args.d_model, 'layers': args.layers, 'heads': args.heads}), metadata['training_counts'], flush=True)
    trainer = Trainer(model, loader, val_loaders, tcfg, asr_loss, model_cfg=cfg, compute_metric=metric, metadata=metadata)
    trainer.train()
    (args.output / 'scratch_report.json').write_text(json.dumps({'params': params, 'steps': args.steps, 'history': history, **metadata},
                                                               ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
