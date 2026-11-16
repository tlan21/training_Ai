"""AI-05 ablation A3: Highlight Fusion image tokens — frozen Siamese backbone (control) vs frozen ViT-classifier backbone.
Metrics registered in TASKS.md: val F1/second at the per-seed tau (swept on val), test F1 + AP scored once at that tau,
mean +- std, Welch t (3 vs 3, low power), parameter count. Reads the kernel's a3_eval.json, no reselection.
  python ablation_A3_compare.py <a3_eval.json> <out.json>
"""
import json
import statistics
import sys

from ablation_A1b_compare import welch

ev = json.load(open(sys.argv[1], encoding='utf-8'))
seeds = (1337, 1338, 1339)
metrics = ('val_f1', 'test_f1', 'test_ap_pooled', 'test_ap_mean_per_half')
runs = {b: [ev['runs'][f'{b}_s{s}'] for s in seeds] for b in ('siamese', 'vit')}
out = {'recipe': ev['recipe'], 'sanity': ev['sanity'], 'seeds': seeds, 'branches': {}, 'diff_vit_minus_siamese': {}}
for b, rs in runs.items():
    out['branches'][b] = {
        'params': rs[0]['params'],
        'tau': [r['tau'] for r in rs],
        'best_step': [r['best_step'] for r in rs],
        **{m: {'per_seed': [r[m] for r in rs], 'mean': statistics.mean(r[m] for r in rs), 'std': statistics.stdev(r[m] for r in rs)} for m in metrics},
    }
for m in metrics:
    a, b = out['branches']['vit'][m]['per_seed'], out['branches']['siamese'][m]['per_seed']
    t, df, p = welch(a, b)
    out['diff_vit_minus_siamese'][m] = {'mean_diff': statistics.mean(a) - statistics.mean(b), 'welch_t': t, 'df': df, 'p': p}
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), indent=1)
for m, d in out['diff_vit_minus_siamese'].items():
    s, v = out['branches']['siamese'][m], out['branches']['vit'][m]
    print(f"{m}: siamese {s['mean']:.4f} +- {s['std']:.4f} | vit {v['mean']:.4f} +- {v['std']:.4f} | diff {d['mean_diff']:+.4f} t={d['welch_t']:.2f} df={d['df']:.1f} p={d['p']:.4f}")
print('params', {b: x['params'] for b, x in out['branches'].items()}, 'tau', {b: x['tau'] for b, x in out['branches'].items()})
