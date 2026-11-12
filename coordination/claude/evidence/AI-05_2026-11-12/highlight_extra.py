"""AI-05 round 2: Highlight Fusion extra metrics on the football TEST split (27 halves / 14 matches), no training, nothing re-selected.

Model = active round-8 x10 ensemble (3 seeds, 5aecd5c4 + 2 members), production recipe (per-video norm, stride 30, k 9, tau 0.51,
merge 1 s, min clip 3 s). Baselines RMS energy (k 3, tau 0.77) and frame-diff (k 45, tau 0.24) = the v5 settings chosen on val.
F1 is recomputed first and must equal the reported values (0.3222 / 0.1440 / 0.1052), else stop.
Extra: AP (threshold-free, pooled valid seconds), Spearman rho score vs label (pooled + mean per half), segment-level P/R/F1 at IoU >= 0.5
(clips built exactly like inference-service _peaks_to_clips), paired bootstrap by match of the F1 gap model - baseline.
  PYTHONPATH=ai-core python highlight_extra.py <out.json>
"""
import json
import os
import sys

import numpy as np
import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.bootstrap_highlight import bootstrap_f1, match_counts
from ai_core.scripts.eval_highlight import frame_diff_scores, model_scores_overlap, rms_scores, smooth
from ai_core.scripts.evaluate import f1_per_second
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets.highlight_dataset import normalize_per_video

FEATURES = 'D:/data_training_ai/kaggle_fusion_140_ds/highlight_features_140.pt'
SEEDS = [f'D:/tmp/ai20/kout/r8_rep10_s{s}/highlight_fusion/best.pt' for s in (1337, 1338, 1339)]
AUDIO, FRAMES = 'D:/data_training_ai/data/processed/soccernet_wav', 'D:/data_training_ai/data/processed/soccernet_keyframes'
METHODS = {'model': (9, .51, .3222), 'rms_energy': (3, .77, .14395280235988203), 'frame_diff': (45, .24, .10518945864956451)}
MERGE, MIN_CLIP, N_BOOT = 1, 3, 10000


def runs(binary):
    out, start = [], None
    for i, v in enumerate(list(binary) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append([start, i])
            start = None
    return out


def clips(score, tau):  # == inference-service _peaks_to_clips without ASR snapping
    merged = []
    for a, b in runs(score > tau):
        if merged and a - merged[-1][1] <= MERGE:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged if b - a >= MIN_CLIP]


def iou(x, y):
    inter = max(0, min(x[1], y[1]) - max(x[0], y[0]))
    return inter / (max(x[1], y[1]) - min(x[0], y[0]))


def segment_counts(pred, truth):
    used, tp = set(), 0
    for p in sorted(pred, key=lambda p: p[0]):
        best = max(((iou(p, t), j) for j, t in enumerate(truth) if j not in used), default=(0, None))
        if best[0] >= .5:
            used.add(best[1])
            tp += 1
    return tp, len(pred), len(truth)


def average_precision(score, label):
    order = np.argsort(-score, kind='stable')
    hits = label[order]
    precision = np.cumsum(hits) / np.arange(1, len(hits) + 1)
    return float((precision * hits).sum() / max(hits.sum(), 1))


def rank(x):  # average ranks for ties
    order = np.argsort(x, kind='stable')
    r = np.empty(len(x))
    r[order] = np.arange(len(x))
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=r)
    return sums[inv] / counts[inv]


def spearman(x, y):
    a, b = rank(x), rank(y)
    return float(np.corrcoef(a, b)[0, 1])


@torch.no_grad()
def model_scores(test):
    models = []
    for path in SEEDS:
        ckpt = load_checkpoint(path)
        m = build_model('highlight_fusion', ModelConfig(**ckpt['config'])).eval()
        m.load_state_dict(ckpt['state_dict'])
        models.append(m)
    out = []
    for h in test:
        s = {'vision': normalize_per_video(h['vision']), 'audio': normalize_per_video(h['audio'])}
        out.append(torch.stack([model_scores_overlap(m, s, 120, 30) for m in models]).mean(0))
    return out


def main():
    test = torch.load(FEATURES, map_location='cpu', weights_only=False, mmap=True)['test']
    names, labels = [h['name'] for h in test], [h['labels'].long() for h in test]
    raw = {'model': model_scores(test)}
    print('model scores done', flush=True)
    raw['rms_energy'] = [rms_scores(os.path.join(AUDIO, f'{n}.wav'), lab.shape[0]) for n, lab in zip(names, labels)]
    print('rms done', flush=True)
    raw['frame_diff'] = [frame_diff_scores(os.path.join(FRAMES, n), lab.shape[0]) for n, lab in zip(names, labels)]
    print('frame-diff done', flush=True)
    report, counts = {'test_halves': len(test), 'test_matches': len({n.split('h')[0] for n in names}),
                      'valid_seconds': int(sum((lab != -1).sum() for lab in labels))}, {}
    for name, (k, tau, reported) in METHODS.items():
        sm = [smooth(s, k) for s in raw[name]]
        f1 = f1_per_second(torch.cat(sm), torch.cat(labels), thresh=tau)
        assert abs(f1 - reported) < 5e-5, f'{name}: recomputed F1 {f1:.6f} != reported {reported:.6f}'
        counts[name] = match_counts([(s > tau).long() for s in sm], labels, names)
        valid = [(s.numpy()[(lab != -1).numpy()], (lab[lab != -1] == 1).numpy().astype(float)) for s, lab in zip(sm, labels)]
        score, label = np.concatenate([v[0] for v in valid]), np.concatenate([v[1] for v in valid])
        seg = np.array([segment_counts(clips(s.numpy(), tau), runs((lab == 1).numpy())) for s, lab in zip(sm, labels)]).sum(0)
        p, r = seg[0] / max(seg[1], 1), seg[0] / max(seg[2], 1)
        report[name] = {'k': k, 'tau': tau, 'f1_per_second': f1, 'ap_pooled': average_precision(score, label),
                        'ap_mean_per_half': float(np.mean([average_precision(s, y) for s, y in valid if y.sum()])),
                        'positive_rate': float(label.mean()),
                        'spearman_pooled': spearman(score, label),
                        'spearman_mean_per_half': float(np.mean([spearman(s, y) for s, y in valid if 0 < y.sum() < len(y)])),
                        'segment_iou50': {'tp': int(seg[0]), 'pred': int(seg[1]), 'truth': int(seg[2]), 'precision': p, 'recall': r,
                                          'f1': 2 * p * r / max(p + r, 1e-12)}}
        print(name, json.dumps(report[name]), flush=True)
    boot = bootstrap_f1(counts, N_BOOT, 0)
    report['bootstrap_by_match'] = {b: {'point': report['model']['f1_per_second'] - report[b]['f1_per_second'],
                                        'ci95': [float(np.percentile(boot['model'] - boot[b], 2.5)), float(np.percentile(boot['model'] - boot[b], 97.5))],
                                        'p_gap_ge_0.10': float(((boot['model'] - boot[b]) >= .10).mean())}
                                    for b in ('rms_energy', 'frame_diff')}
    report['bootstrap_by_match']['n_boot'], report['bootstrap_by_match']['seed'] = N_BOOT, 0
    print('bootstrap', json.dumps(report['bootstrap_by_match']), flush=True)
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)


if __name__ == '__main__':
    main()
