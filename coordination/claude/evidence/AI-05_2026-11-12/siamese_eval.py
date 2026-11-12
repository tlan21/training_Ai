"""AI-05 round 2: re-measure Siamese visual search (active b4ded465) on the original test protocol + mAP/MRR.

Protocol = Kaggle notebook cell 15 "3b": shot groups from frames_jpg_80.json (JPGs now read from frames_jpg_100, same files for the
160 original halves), test split = first sorted test halves until 10,000 frames (expect g07h2/g13h1/g20h2/g25h2 = 10,227 frames);
1,000 queries = randperm seed 0; pair = 2 views of the same shot 1-10 s apart (SiamesePairDataset). The pair/jitter draw uses global
RNG (not reproducible in the original), so the eval is repeated with 5 RNG seeds; logged original: R@1 .362 R@5 .722 R@10 .804.
With one relevant item per query, mAP = MRR.
  PYTHONPATH=ai-core python siamese_eval.py <workdir> <out.json>
"""
import json
import random
import statistics
import sys
from pathlib import Path

import torch

from ai_core import build_model
from ai_core.baselines import downscale, histogram_features
from ai_core.config import ModelConfig
from ai_core.scripts import build_shot_groups
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets import SiamesePairDataset

SRC = 'D:/data_training_ai/data/manifests/frames_jpg_80.json'
CKPT = 'E:/traning_ai/ai-core/checkpoints/siamese/best.pt'
EXPECTED_TEST = {'g07h2', 'g13h1', 'g20h2', 'g25h2'}


def metrics(ea, eb):
    order = (ea @ eb.T).argsort(dim=1, descending=True)
    rank = (order == torch.arange(len(order)).unsqueeze(1)).float().argmax(dim=1) + 1
    return {'R@1': float((rank <= 1).float().mean()), 'R@5': float((rank <= 5).float().mean()),
            'R@10': float((rank <= 10).float().mean()), 'median_rank': int(rank.sort().values[len(rank) // 2]),
            'mAP_MRR': float((1.0 / rank).mean())}


def main():
    work, out = Path(sys.argv[1]), Path(sys.argv[2])
    work.mkdir(parents=True, exist_ok=True)
    shots = work / 'shots_test.json'
    if not shots.exists():
        man = json.load(open(SRC, encoding='utf-8'))
        man['items'] = [dict(i, path=i['path'].replace('/frames_jpg_80/', '/frames_jpg_100/')) for i in man['items'] if i['split'] == 'test']
        for i in man['items']:
            i['extra'].pop('src', None)
        (work / 'frames_test.json').write_text(json.dumps(man), encoding='utf-8')
        sys.argv = ['build_shot_groups', '--manifest', str(work / 'frames_test.json'), '--out-manifest', str(shots), '--max-frames', '100000']
        build_shot_groups.main()  # train/val absent -> only the test budget (10,000) is filled, same order as the original
    te = SiamesePairDataset(str(shots), 'test', 224)
    halves = {it.extra['half'] for it in te.items} if hasattr(te, 'items') else None
    ckpt = load_checkpoint(CKPT, map_location='cpu')
    model = build_model('siamese', ModelConfig(**ckpt['config'])).eval()
    model.load_state_dict(ckpt['state_dict'])
    idx = torch.randperm(len(te), generator=torch.Generator().manual_seed(0))[:min(1000, len(te))]
    report = {'test_frames': len(te), 'test_halves': sorted(halves) if halves else None, 'queries': len(idx), 'runs': {}}
    norm = torch.nn.functional.normalize
    for seed in range(5):
        torch.manual_seed(seed)
        random.seed(seed)
        te.rng = random.Random(1337 if seed == 0 else seed)  # run 0 = the original partner draws (dataset rng seed 1337)
        A = torch.stack([te[int(i)][0] for i in idx])
        B = torch.stack([te[int(i)][1] for i in idx])
        with torch.no_grad():
            ea = torch.cat([model.encode(A[i:i + 64]).float() for i in range(0, len(A), 64)])
            eb = torch.cat([model.encode(B[i:i + 64]).float() for i in range(0, len(B), 64)])
        report['runs'][seed] = {'siamese': metrics(ea, eb),
                                'histogram': metrics(norm(histogram_features(A), dim=-1), norm(histogram_features(B), dim=-1)),
                                'template16': metrics(norm(downscale(A, 16), dim=-1), norm(downscale(B, 16), dim=-1))}
        print(seed, json.dumps(report['runs'][seed]), flush=True)
    report['mean_std'] = {m: {k: [statistics.mean(r[m][k] for r in report['runs'].values()), statistics.stdev(r[m][k] for r in report['runs'].values())]
                              for k in ('R@1', 'R@5', 'R@10', 'median_rank', 'mAP_MRR')} for m in ('siamese', 'histogram', 'template16')}
    out.write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(json.dumps(report['mean_std']), flush=True)


if __name__ == '__main__':
    main()
