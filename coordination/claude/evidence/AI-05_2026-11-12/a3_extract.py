"""AI-05 ablation A3: frozen ViT-classifier backbone embeddings (variant) for the exact seconds of highlight_features_140.pt.

Same image path as the control (extract_vit_embeddings: resize to img_size, /255, backbone embedding, no projection head).
Registered alignment check first: the frozen Siamese backbone on these same JPGs must reproduce the control `vision` rows
(mean cosine >= 0.99 over 3 halves, 200 evenly spaced seconds each) — else stop. One file per half (resume-safe).
  python a3_extract.py <features_140.pt> <frames_root> <vit.pt> <siamese.pt> <out_dir> <first_game> <last_game>   (e.g. 0 99)
"""
import re
import os
import sys

import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.extract_vit_embeddings import _load_image
from ai_core.training.checkpoint import load_checkpoint

BATCH = 64


def backbone_of(path, device):
    ckpt = load_checkpoint(path, map_location='cpu')
    cfg = ModelConfig(**ckpt['config'])
    model = build_model(ckpt['config'].get('name', 'vit'), cfg).eval()
    model.load_state_dict(ckpt['state_dict'])
    model.to(device)
    return (model.backbone if hasattr(model, 'backbone') else model), cfg.img_size


_INDEX = {}


def frame_dir(root, name):
    if not _INDEX:  # one walk; stop at half folders (g12h1) so the ~2700 files inside are never listed
        for d, dirs, _ in os.walk(root):
            for sub in [s for s in dirs if re.fullmatch(r'g\d+h[12]', s)]:
                if sub in _INDEX:
                    raise SystemExit(f'{sub}: two frame folders ({_INDEX[sub]}, {d})')
                _INDEX[sub] = os.path.join(d, sub)
            dirs[:] = [s for s in dirs if not re.fullmatch(r'g\d+h[12]', s)]
    if name not in _INDEX or not os.path.exists(os.path.join(_INDEX[name], f'{name}_s00000.jpg')):
        raise SystemExit(f'{name}: no frame folder under {root}')
    return _INDEX[name]


def game(name):
    return int(name[1:].split('h')[0])


@torch.no_grad()
def embed(backbone, size, folder, name, secs, device):
    out = []
    for i in range(0, len(secs), BATCH):
        batch = torch.stack([_load_image(os.path.join(folder, f'{name}_s{s:05d}.jpg'), size) for s in secs[i:i + BATCH]]).to(device)
        out.append(backbone(batch, return_embedding=True)[1].float().cpu())
    return torch.cat(out)


def main():
    feats, root, vit_ckpt, sia_ckpt, out_dir = sys.argv[1:6]
    lo, hi = int(sys.argv[6]), int(sys.argv[7])
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    os.makedirs(out_dir, exist_ok=True)
    data = torch.load(feats, map_location='cpu', weights_only=False)
    rows = [(h, split) for split in ('train', 'val', 'test') for h in data[split] if lo <= game(h['name']) <= hi]
    halves = [(h['name'], h['vision'].shape[0], split) for h, split in rows]
    control = {rows[i][0]['name']: rows[i][0]['vision'] for i in (0, len(rows) // 2, len(rows) - 1)}  # 3 halves spread over the range
    del data
    print(f'device {device} | halves in g{lo}..g{hi}: {len(halves)} | seconds {sum(t for _, t, _ in halves)}', flush=True)

    sia, size = backbone_of(sia_ckpt, device)
    cos = []
    for name, ref in control.items():
        secs = torch.linspace(0, ref.shape[0] - 1, 200).long().tolist()
        emb = embed(sia, size, frame_dir(root, name), name, secs, device)
        cos.append(float(torch.nn.functional.cosine_similarity(emb, ref[secs].float()).mean()))
    print(f'ALIGNMENT siamese vs control {list(control)}: mean cosine {[round(c, 4) for c in cos]}', flush=True)
    if min(cos) < 0.99:
        raise SystemExit('ALIGNMENT FAIL — frames/preprocessing do not reproduce the control features; stop (registered rule)')
    del sia

    vit, size = backbone_of(vit_ckpt, device)
    for k, (name, T, split) in enumerate(halves, 1):
        dest = os.path.join(out_dir, f'{name}.pt')
        if os.path.exists(dest):
            continue
        emb = embed(vit, size, frame_dir(root, name), name, list(range(T)), device)
        assert emb.shape == (T, 256), emb.shape
        torch.save(emb, dest + '.tmp')
        os.replace(dest + '.tmp', dest)
        print(f'[{k}/{len(halves)}] {name} {split} {T}', flush=True)
    print('A3 EXTRACT DONE', flush=True)


if __name__ == '__main__':
    main()
