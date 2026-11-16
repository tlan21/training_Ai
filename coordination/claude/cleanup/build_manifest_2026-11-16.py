"""AI-08 round 3: build cleanup manifest (read-only: size, sha256, class, reason, kept copy). Exits if a 'duplicate' is not identical."""
import hashlib
import json
import os
import sys

D, T, E = 'D:/data_training_ai', 'D:/tmp/ai25', 'E:/traning_ai/ai-core/checkpoints'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def files(path):
    if os.path.isfile(path):
        return [path]
    return sorted(os.path.join(r, f) for r, _, fs in os.walk(path) for f in fs)


groups = {
    'A': ('REGENERABLE', 'A3 CPU smoke workspace: input/ = byte-identical copies of kept A3 inputs; out/ckpt = 30-step smoke '
          'checkpoints (no number depends on them). Keep run_smoke.py + out/a3_eval.json.',
          [(f'{T}/a3smoke/input/ctrl/highlight_features_140.pt', f'{D}/kaggle_fusion_140_ds/highlight_features_140.pt'),
           (f'{T}/a3smoke/input/vit', f'{D}/a3_vit_halves'),
           (f'{T}/a3smoke/out/ckpt_siamese_s1337', None), (f'{T}/a3smoke/out/ckpt_vit_s1337', None)]),
    'B': ('REGENERABLE', 'Byte-identical duplicate (sha256) of a file that stays; Kaggle upload copies. Restore = cp from kept copy '
          'if that Kaggle dataset version is ever re-pushed.',
          [(f'{D}/asr_football_replay_v2_20261106/kaggle_dataset/source_asr.pt', f'{E}/asr_ctc/best.pt'),
           (f'{D}/asr_football_replay_v3_20261111/kaggle_dataset/source_asr.pt', f'{E}/asr_ctc/best.pt'),
           (f'{D}/asr_public_expand_v1_20261105/kaggle_dataset/source_asr.pt', f'{E}/asr_ctc/best.pt'),
           (f'{D}/asr_football_replay_v1_20261105/kaggle_dataset/source_asr.pt', f'{E}/_archive/asr_ctc_8f879867/best.pt'),
           (f'{D}/asr_robust/kaggle_dataset/source_asr.pt', f'{E}/_archive/asr_ctc_8f879867/best.pt'),
           (f'{D}/asr_domain_replay_v1_20261021/kaggle_dataset/source_asr.pt', f'{D}/asr_three_source_v1_20261020/kaggle_dataset/source_asr.pt'),
           (f'{D}/asr_domain_replay_v1_20261021_incomplete_reference_hash/kaggle_dataset/source_asr.pt',
            f'{D}/asr_three_source_v1_20261020/kaggle_dataset/source_asr.pt'),
           (f'{D}/asr_domain_replay_v2_20261028/kaggle_dataset/source_asr.pt', f'{D}/asr_three_source_v1_20261020/kaggle_dataset/source_asr.pt'),
           (f'{D}/minigpt_football_v1/upload/active.pt', f'{E}/_archive/minigpt_cf9cfa71/best.pt'),
           (f'{D}/minigpt_football_v2/upload/active.pt', f'{E}/_archive/minigpt_cf9cfa71/best.pt'),
           (f'{D}/asr_public_expand_v1_20261105/kaggle_dataset/domain_audio.zip',
            f'{D}/asr_football_replay_v1_20261105/kaggle_dataset/domain_audio.zip')]),
    'C': ('REGENERABLE', 'Old overlay deploy build contexts (copied src + go-built gateway binary); images already built, source = '
          'git commit. Keep deploy064 (latest).',
          [(f'{T}/deploy012', None), (f'{T}/deploy061', None), (f'{T}/deploy062', None), (f'{T}/deploy063', None)]),
}
out, total = {'date': '2026-11-16', 'round': 3, 'groups': {}}, 0
for g, (cls, reason, items) in groups.items():
    rows, gsum = [], 0
    for path, kept in items:
        fl = files(path)
        size = sum(os.path.getsize(f) for f in fl)
        row = {'path': path, 'bytes': size, 'files': len(fl), 'kept_copy': kept}
        if kept:
            ref = [kept] if os.path.isfile(kept) else [os.path.join(kept, os.path.basename(a)) for a in fl]
            names_ok = all(os.path.isfile(b) for b in ref)
            pairs = [(sha(a), sha(b)) for a, b in zip(fl, ref)] if names_ok else []
            if not names_ok or any(a != b for a, b in pairs):
                sys.exit(f'NOT A DUPLICATE: {path}')
            row['sha256'] = pairs[0][0] if len(pairs) == 1 else {os.path.basename(a): p[0] for a, p in zip(fl, pairs)}
        else:
            row['files_sha256'] = {os.path.relpath(f, path).replace('\\', '/'): [os.path.getsize(f), sha(f)] for f in fl}
        rows.append(row)
        gsum += size
    out['groups'][g] = {'class': cls, 'reason': reason, 'bytes': gsum, 'items': rows}
    total += gsum
out['total_bytes'] = total
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), indent=1)
for g, v in out['groups'].items():
    print(g, v['class'], f"{v['bytes']:,}", len(v['items']), 'items')
print('TOTAL', f'{total:,}')
