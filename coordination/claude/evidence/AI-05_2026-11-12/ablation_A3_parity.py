"""AI-05 A3: the downloaded best.pt files are the ones the kernel scored — strict load on CPU, recompute test F1 at the
recorded tau (no reselection), must match a3_eval.json to 1e-6.
  python ablation_A3_parity.py <a3_eval.json> <ckpt root> <highlight_features_140.pt> <vit halves dir>
"""
import json
import sys

import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.eval_highlight import model_scores
from ai_core.scripts.evaluate import f1_per_second
from ai_core.training.checkpoint import load_checkpoint

ev, root, ctrl, vit_dir = json.load(open(sys.argv[1], encoding='utf-8')), sys.argv[2], sys.argv[3], sys.argv[4]
test = torch.load(ctrl, map_location='cpu', weights_only=False)['test']
data = {'siamese': test, 'vit': [{**h, 'vision': torch.load(f"{vit_dir}/{h['name']}.pt", map_location='cpu')} for h in test]}
labels = torch.cat([h['labels'] for h in test])
bad = 0
for key, run in ev['runs'].items():
    ckpt = load_checkpoint(f"{root}/ckpt_{key}/highlight_fusion/best.pt")
    cfg = ModelConfig(**ckpt['config'])
    model = build_model('highlight_fusion', cfg)
    model.load_state_dict(ckpt['state_dict'], strict=True)
    model.eval()
    with torch.no_grad():
        score = torch.cat([model_scores(model, h, cfg.window_seconds) for h in data[run['branch']]])
    f1 = f1_per_second(score, labels, thresh=run['tau'])
    ok = abs(f1 - run['test_f1']) < 1e-6
    bad += not ok
    print(f"{key}: strict load OK | test F1 local {f1:.6f} kernel {run['test_f1']:.6f} {'MATCH' if ok else 'MISMATCH'}")
print('PARITY', 'PASS' if bad == 0 else f'FAIL ({bad})')
