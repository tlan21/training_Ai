"""AI-27: score active vs candidate ASR once on the registered tests with the same greedy decode as inference-service.

  python eval_asr_tests.py <active best.pt> <candidate .pt> <out.json>
football = 30 held-out-channel clips (AI-25 export); VIVOS test 760; FLEURS test 857 (read from fleurs_audio.zip).
"""
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

from lm_tune import acoustic, score

FOOTBALL = Path('D:/data_training_ai/football_asr_sources/received_v1/intake/approved.json')
VIVOS = Path('D:/data_training_ai/data/manifests/vivos.json')
ROBUST = Path('D:/data_training_ai/asr_robust/kaggle_dataset')


def main():
    active, candidate, out = sys.argv[1:4]
    zf = zipfile.ZipFile(ROBUST / 'fleurs_audio.zip')
    robust = json.loads((ROBUST / 'asr_robust_manifest.json').read_text(encoding='utf-8'))
    sets = {
        'football': [{'src': a['path'], 'ref': a['extra']['transcript']}
                     for a in json.loads(FOOTBALL.read_text(encoding='utf-8')) if a['split'] == 'val'],
        'vivos_test': [{'src': i['path'], 'ref': i['extra']['transcript']}
                       for i in json.loads(VIVOS.read_text(encoding='utf-8'))['items'] if i['split'] == 'test'],
        'fleurs_test': [{'src': i['path'], 'ref': i['extra']['transcript']}
                        for i in robust['items'] if i['extra']['source'] == 'fleurs' and i['split'] == 'test'],
    }
    report = {'active': active, 'candidate': candidate, 'sizes': {k: len(v) for k, v in sets.items()}}
    per = {}
    for role, ckpt in (('active', active), ('candidate', candidate)):
        rows_of, _ = acoustic(ckpt)
        for name, items in sets.items():
            hyps = [rows_of(io.BytesIO(zf.read(i['src'])) if name == 'fleurs_test' else i['src'])[1] for i in items]
            c, w, cs = score(items, hyps)
            per[(role, name)] = cs
            report.setdefault(name, {})[role] = {'cer': c, 'wer': w}
            print(role, name, round(c, 4), round(w, 4), flush=True)
    for name in sets:
        d = np.array(per[('candidate', name)]) - np.array(per[('active', name)])
        rng = np.random.default_rng(1337)
        report[name]['delta_cer'] = float(d.mean())
        report[name]['delta_cer_ci95'] = np.quantile([rng.choice(d, len(d)).mean() for _ in range(2000)], [.025, .975]).tolist()
    Path(out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
