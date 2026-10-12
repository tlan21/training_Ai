"""throwaway probe: does history=fit vs fit+val change the reported gap? delete after."""
import time, torch
from torch.utils.data import DataLoader
from ai_core.config import ModelConfig, TrainConfig
from ai_core.models.two_tower import TwoTower
from ai_core.training import Trainer
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets import BPRTripleDataset, build_features, leave_last_k_split
from ai_core.training.loss_fns import two_tower_softmax_loss
from ai_core.scripts.evaluate import eval_recommender

ML = 'E:/traning_ai/dist/kaggle/ai-core-ds'
n_genre = 19
item_genres = {}
for line in open(ML + '/u.item', encoding='latin-1'):
    p = line.rstrip('\n').split('|')
    item_genres[int(p[0])] = torch.tensor([float(x) for x in p[-n_genre:]], dtype=torch.float32)
rows = []
for line in open(ML + '/u.data'):
    u, i, r, ts = map(int, line.split())
    if r >= 4:
        rows.append((u, i, ts))
train_rows, test_rows = leave_last_k_split(rows, k=10)
fit_rows, val_rows = leave_last_k_split(train_rows, k=10)
user_feat, video_feat = build_features(fit_rows, item_genres)
print('fit', len(fit_rows), 'val', len(val_rows), 'test', len(test_rows), flush=True)

MAX = int(__import__('sys').argv[1]) if len(__import__('sys').argv) > 1 else 3000
ds = BPRTripleDataset(fit_rows, user_feat, video_feat, len(video_feat), seed=1337, neg_alpha=1.0)
ld = DataLoader(ds, batch_size=256, shuffle=True, drop_last=True)
ud = next(iter(user_feat.values())).numel(); vd = next(iter(video_feat.values())).numel()
mcfg = ModelConfig(name='two_tower', proj_dim=128, temperature=0.1, user_dim=ud, video_dim=vd)
model = TwoTower(mcfg, user_dim=ud, video_dim=vd)
tcfg = TrainConfig(model='two_tower', lr=1e-3, max_steps=MAX, warmup_ratio=0.05, batch_size=256,
                   seed=1337, ckpt_dir='E:/traning_ai/ai-core/_probe_ckpt', log_dir='',
                   eval_every=500, metric_name='ndcg_at_10')

def val_ndcg(m, r, device):
    return eval_recommender(m, user_feat, video_feat, fit_rows, r, k=10, device=device)['model_ndcg']

t0 = time.time()
tr = Trainer(model, ld, val_rows, tcfg, loss_fn=two_tower_softmax_loss, model_cfg=mcfg,
             compute_metric=val_ndcg)
stats = tr.train()
print('train secs', round(time.time() - t0, 1), stats, flush=True)
best = load_checkpoint('E:/traning_ai/ai-core/_probe_ckpt/two_tower/best.pt', map_location=tr.device)
model.load_state_dict(best['state_dict'])
print('best metrics', best['metrics'], flush=True)
for label, hist in (('hist=fit_rows (new notebook)', fit_rows), ('hist=fit+val (train_rows)', train_rows)):
    m = eval_recommender(model, user_feat, video_feat, hist, test_rows, k=10, device=tr.device)
    print(f"{label}: model_ndcg={m['model_ndcg']:.4f} pop_ndcg={m['pop_ndcg']:.4f} "
          f"gap={m['model_ndcg']-m['pop_ndcg']:+.4f} | model_recall={m['model_recall']:.4f} "
          f"pop_recall={m['pop_recall']:.4f} n={m['n_users']}", flush=True)
