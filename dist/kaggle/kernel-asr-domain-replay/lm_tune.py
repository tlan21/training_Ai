"""AI-26: tune alpha/beta of lexicon+bigram CTC decoding on dev only, then score the pre-registered test once.

dev  = 14 football train clips (AI-25 export) + 10 frozen news-domain val clips (AI-02); never the test sets.
test = 30 football eval clips (held-out channels) + VIVOS test (760); greedy vs beam+LM with the dev-chosen setting.

  python lm_tune.py <asr best.pt> <lm.json> <out.json>
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from football_intake import normalize, cer, wer  # same scorer + label normalization as AI-25 (also puts ai-core on sys.path)
from ai_core import build_model
from ai_core.audio.mel import log_mel_spectrogram
from ai_core.config import ModelConfig
from ai_core.models.ctc import ctc_greedy_decode
from ai_core.models.ctc_lm import SyllableLM, ctc_lm_decode
from ai_core.training.checkpoint import load_checkpoint

FOOTBALL = Path('D:/data_training_ai/football_asr_sources/received_v1/intake/approved.json')
NEWS = Path('D:/data_training_ai/minigpt_domain_v1_20261019/asr_verbatim_v1')
VIVOS = Path('D:/data_training_ai/data/manifests/vivos.json')
GRID = [(a, b, p, o) for a in (0.1, 0.2, 0.3, 0.5) for b in (2.0, 3.0, 4.0, 6.0) for p in (0.0, -1.0) for o in (-5.0, -10.0)]


def acoustic(checkpoint):
    ckpt = load_checkpoint(str(checkpoint), map_location='cpu')
    model = build_model('asr_ctc', ModelConfig(**ckpt['config']))
    model.load_state_dict(ckpt['state_dict'])
    model.eval()
    vocab = ckpt.get('char_vocab') or ckpt['metadata']['char_vocab']

    def rows(path):
        signal = torch.tensor(sf.read(path if hasattr(path, 'read') else str(path), dtype='float32')[0])
        mel = log_mel_spectrogram(signal, n_mels=80, sr=16000).unsqueeze(0)
        with torch.no_grad():
            lp, n = model(mel, torch.tensor([mel.shape[2]]))
        lp = lp.float()
        greedy = ''.join(vocab[i] for i in ctc_greedy_decode(lp, n, blank=0)[0] if 0 < i < len(vocab))
        return lp[0, :int(n[0])].tolist(), greedy
    return rows, vocab


def score(items, hyps):
    hyps = [normalize(h) if h.strip() else '' for h in hyps]  # an empty decode scores as all-deletion, never skipped
    c = [cer(i['ref'], h) for i, h in zip(items, hyps)]
    w = [wer(i['ref'], h) for i, h in zip(items, hyps)]
    return float(np.mean(c)), float(np.mean(w)), c


def main():
    checkpoint, lm_path, out = sys.argv[1:4]
    rows_of, vocab = acoustic(checkpoint)
    lm = SyllableLM.load(lm_path)
    football = json.loads(FOOTBALL.read_text(encoding='utf-8'))
    frozen = json.loads((NEWS / 'frozen_validation.json').read_text(encoding='utf-8'))
    sets = {'dev': [{'path': a['path'], 'ref': a['extra']['transcript']} for a in football if a['split'] == 'train']
            + [{'path': str(NEWS.parent / 'audio' / f"{f['sample_id']}.wav"), 'ref': f['transcript']} for f in frozen],
            'test_football': [{'path': a['path'], 'ref': a['extra']['transcript']} for a in football if a['split'] == 'val'],
            'test_vivos': [{'path': i['path'], 'ref': i['extra']['transcript']}
                           for i in json.loads(VIVOS.read_text(encoding='utf-8'))['items'] if i['split'] == 'test']}
    cache = {k: [rows_of(i['path']) for i in v] for k, v in sets.items() if k == 'dev' or '--test' in sys.argv}
    report = {'lm_sha256': hashlib.sha256(Path(lm_path).read_bytes()).hexdigest(), 'grid': {}, 'sizes': {k: len(v) for k, v in sets.items()}}
    report['dev_greedy'] = score(sets['dev'], [g for _, g in cache['dev']])[:2]
    print('dev greedy', report['dev_greedy'], flush=True)
    for a, b, p, o in GRID:  # dev only
        hyps = [ctc_lm_decode(r, vocab, lm, alpha=a, beta=b, partial=p, oov=o)[0] for r, _ in cache['dev']]
        report['grid'][f'{a},{b},{p},{o}'] = score(sets['dev'], hyps)[:2]
        print('dev', a, b, p, o, report['grid'][f'{a},{b},{p},{o}'], flush=True)
    best = min(report['grid'], key=lambda k: report['grid'][k][0])
    if '--test' not in sys.argv:  # step 1: dev only; the test is scored in a separate run with the frozen setting
        report['dev_best'] = best
        Path(out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
        print('DEV ONLY best', best, flush=True)
        return
    a, b, p, o = map(float, sys.argv[sys.argv.index('--test') + 1].split(','))
    report['chosen'] = {'alpha': a, 'beta': b, 'partial': p, 'oov': o}
    for name in ('test_football', 'test_vivos'):  # scored once with the dev-chosen setting
        t0 = time.time()
        lm_hyps = [ctc_lm_decode(r, vocab, lm, alpha=a, beta=b, partial=p, oov=o)[0] for r, _ in cache[name]]
        seconds = (time.time() - t0) / len(lm_hyps)
        g_cer, g_wer, g_c = score(sets[name], [g for _, g in cache[name]])
        l_cer, l_wer, l_c = score(sets[name], lm_hyps)
        d = np.array(l_c) - np.array(g_c)
        rng = np.random.default_rng(1337)
        ci = np.quantile([rng.choice(d, len(d)).mean() for _ in range(2000)], [.025, .975]).tolist()
        report[name] = {'greedy': {'cer': g_cer, 'wer': g_wer}, 'lm': {'cer': l_cer, 'wer': l_wer}, 'delta_cer': float(d.mean()),
                        'delta_cer_ci95': ci, 'decode_seconds_per_item': seconds,
                        'examples': [{'ref': i['ref'][:120], 'greedy': g[:120], 'lm': h[:120]}
                                     for i, (_, g), h in list(zip(sets[name], cache[name], lm_hyps))[:5]]}
        print(name, json.dumps({k: v for k, v in report[name].items() if k != 'examples'}), flush=True)
    Path(out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
