"""AI-05 ablation A1b: ViT Post-LN (warmup in sanity) vs the project Pre-Norm control — the metrics registered in TASKS.md.
Top-1 + macro-F1 mean +- std, Welch t (3 vs 3, low power), val accuracy curves, parameter count. No retraining, no reselection.
  python ablation_A1b_compare.py <postln_dir> <control_dir> <out.json>
"""
import json
import re
import statistics
import sys
from pathlib import Path

import torch


def welch(a, b):
    # ponytail: no scipy in venv; two-sided p = numeric integral of the Student-t pdf (Welch-Satterthwaite df)
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    t = (statistics.mean(a) - statistics.mean(b)) / (va + vb) ** 0.5
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    x = torch.linspace(abs(t), abs(t) + 2000, 2_000_001, dtype=torch.float64)
    pdf = torch.distributions.StudentT(torch.tensor(df, dtype=torch.float64)).log_prob(x).exp()
    return t, df, float(2 * torch.trapezoid(pdf, x))


def summary(d):
    ev = json.load(open(d / 'vit_eval.json', encoding='utf-8'))
    runs = ev['model']['runs']
    out = {k: [r[k] for r in runs] for k in ('top1', 'macro_f1')}
    out['per_class_f1_mean'] = {c: statistics.mean(r['per_class_f1'][c] for r in runs) for c in ev['classes']}
    out['bong_da_youtube_top1_mean'] = statistics.mean(r['bong_da_youtube_top1'] for r in runs)
    curves = {}
    for s in (1337, 1338, 1339):
        h = d / f'vit_s{s}' / 'vit' / 'history.json'
        if h.exists():
            rows = json.load(open(h, encoding='utf-8'))
            curves[s] = {'val_acc': [round(r['accuracy'], 4) for r in rows if r.get('accuracy') is not None],
                         'best_val_acc': max(r['accuracy'] for r in rows if r.get('accuracy') is not None),
                         'final_train_loss': rows[-1]['train_loss_mean']}
    if not curves and (d / 'ai-core-vit.log').exists():  # control run kept no history.json; its log has "step N | accuracy X"
        log = (d / 'ai-core-vit.log').read_text(encoding='utf-8')
        pts = [(int(a), float(b)) for a, b in re.findall(r'step (\d+) \| accuracy ([0-9.]+)', log) if int(a) % 1000 == 0]
        runs, cur = [], []
        for st, acc in pts:
            if cur and st <= cur[-1][0]:
                runs.append(cur)
                cur = []
            cur.append((st, acc))
        runs.append(cur)
        assert len(runs) == 3, [len(r) for r in runs]
        curves = {s: {'val_acc': [a for _, a in r], 'best_val_acc': max(a for _, a in r), 'final_train_loss': None}
                  for s, r in zip((1337, 1338, 1339), runs)}
    out['curves'] = curves
    ck = torch.load(d / 'vit_s1337' / 'vit' / 'best.pt', map_location='cpu', weights_only=False)
    out['params'] = sum(v.numel() for v in ck['state_dict'].values())
    return out


def main():
    post, ctrl, dest = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    a, b = summary(post), summary(ctrl)
    rep = {'postln': a, 'prenorm_control': b}
    for k in ('top1', 'macro_f1'):
        t, df, p = welch(a[k], b[k])
        rep[k] = {'postln_mean_std': [statistics.mean(a[k]), statistics.stdev(a[k])],
                  'prenorm_mean_std': [statistics.mean(b[k]), statistics.stdev(b[k])],
                  'diff': statistics.mean(a[k]) - statistics.mean(b[k]), 'welch_t': t, 'welch_df': df, 'p_two_sided': p}
    dest.write_text(json.dumps(rep, indent=1), encoding='utf-8')
    print(json.dumps({k: rep[k] for k in ('top1', 'macro_f1')}, indent=1))
    print('params', a['params'], b['params'])
    for name, s in (('postln', a), ('prenorm', b)):
        for seed, c in s['curves'].items():
            print(name, seed, 'best_val', round(c['best_val_acc'], 4), 'final_train_loss', c['final_train_loss'] and round(c['final_train_loss'], 4), 'val', c['val_acc'])


def _check():  # known value: t=0 -> p=1; df=2, t=4.303 -> p~0.05
    x = torch.linspace(4.303, 2004.303, 2_000_001, dtype=torch.float64)
    p = float(2 * torch.trapezoid(torch.distributions.StudentT(torch.tensor(2.0, dtype=torch.float64)).log_prob(x).exp(), x))
    assert abs(p - 0.05) < 1e-3, p


if __name__ == '__main__':
    _check()
    main()

