"""AI-05 ablation A2: MiniGPT RoPE (project) vs learned positional embedding — the metrics registered in TASKS.md.
Val perplexity at ctx 256 (main) / 512 / 1024 (extrapolation), mean +- std, Welch t (3 vs 3, low power), parameter count.
Final checkpoints only, no reselection.
  python ablation_A2_compare.py <pe_eval.json> <out.json>
"""
import json
import statistics
import sys

from ablation_A1b_compare import welch

ev = json.load(open(sys.argv[1], encoding='utf-8'))
seeds = (1337, 1338, 1339)
runs = {v: [ev['runs'][f'{v}_s{s}'] for s in seeds] for v in ('rope', 'learned')}
out = {'N_steps': ev['N'], 'tokens_per_step': ev['tokens_per_step'], 'eval_tokens': ev['eval_tokens'], 'seeds': seeds, 'variants': {}, 'diff_learned_minus_rope': {}}
for v, rs in runs.items():
    out['variants'][v] = {
        'params': rs[0]['params'],
        'ppl': {L: {'per_seed': [r['ppl'][L] for r in rs], 'mean': statistics.mean(r['ppl'][L] for r in rs), 'std': statistics.stdev(r['ppl'][L] for r in rs)} for L in ('256', '512', '1024')},
        'final_train_loss': [r['log'][-1]['train_loss'] for r in rs],
        's_per_step': statistics.mean(r['s_per_step'] for r in rs),
    }
for L in ('256', '512', '1024'):
    a, b = out['variants']['learned']['ppl'][L]['per_seed'], out['variants']['rope']['ppl'][L]['per_seed']
    t, df, p = welch(a, b)
    out['diff_learned_minus_rope'][L] = {'mean_diff': statistics.mean(a) - statistics.mean(b), 'welch_t': t, 'df': df, 'p': p}
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), indent=1)
for L, d in out['diff_learned_minus_rope'].items():
    r, l = out['variants']['rope']['ppl'][L], out['variants']['learned']['ppl'][L]
    print(f"ctx {L}: rope {r['mean']:.2f} +- {r['std']:.2f} | learned {l['mean']:.2f} +- {l['std']:.2f} | diff {d['mean_diff']:+.2f} t={d['welch_t']:.2f} df={d['df']:.1f} p={d['p']:.4f}")
print('params', {v: x['params'] for v, x in out['variants'].items()}, 'final train loss', {v: [round(y, 3) for y in x['final_train_loss']] for v, x in out['variants'].items()})
