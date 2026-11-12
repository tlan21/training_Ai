"""AI-05 round 2: ASR real-time factor (RTF = processing time / audio duration) on CPU — the deployed runtime (container INFER_DEVICE=cpu).

Same path as inference-service worker.asr: log-mel -> model -> CTC greedy decode, one clip at a time, warm-up excluded.
Audio: first 200 VIVOS test utterances (short read speech) + 59 football test clips (20 s). Threads: torch default and 1.
  python asr_rtf.py <out.json>
"""
import json
import statistics
import sys
import time
from pathlib import Path

import soundfile as sf
import torch

sys.path.insert(0, 'E:/traning_ai/ai-core')
from ai_core import build_model  # noqa: E402
from ai_core.audio.mel import log_mel_spectrogram  # noqa: E402
from ai_core.config import ModelConfig  # noqa: E402
from ai_core.training.checkpoint import load_checkpoint  # noqa: E402
from ai_core.models.ctc import ctc_greedy_decode  # noqa: E402

MODELS = {'active_7c497d43': 'E:/traning_ai/ai-core/checkpoints/asr_ctc/best.pt',
          'ai29_s3_2c6b7fab_25.6M': 'D:/data_training_ai/asr_scratch_v2_20261109/output/asr_scratch/asr_ctc/best.pt'}
VIVOS = 'D:/data_training_ai/data/manifests/vivos.json'
FOOTBALL = ['D:/data_training_ai/football_asr_sources/received_v1/intake/approved.json',
            'D:/data_training_ai/football_asr_sources/received_v2/intake/approved.json']


def clips():
    vivos = [i['path'] for i in json.load(open(VIVOS, encoding='utf-8'))['items'] if i['split'] == 'test'][:200]
    football = [a['path'] for f in FOOTBALL for a in json.load(open(f, encoding='utf-8')) if a['split'] == 'val']
    return {'vivos_test_200': vivos, 'football_test_59': football}


def run(model, path):
    signal = torch.tensor(sf.read(str(path), dtype='float32')[0])
    t0 = time.perf_counter()
    mel = log_mel_spectrogram(signal, n_mels=80, sr=16000).unsqueeze(0)
    with torch.no_grad():
        lp, n = model(mel, torch.tensor([mel.shape[2]]))
    ctc_greedy_decode(lp.float(), n, blank=0)
    return time.perf_counter() - t0, len(signal) / 16000


def main():
    default = torch.get_num_threads()
    sets, report = clips(), {'cpu_threads_default': default, 'torch': torch.__version__}
    for name, path in MODELS.items():
        ckpt = load_checkpoint(path, map_location='cpu')
        model = build_model('asr_ctc', ModelConfig(**ckpt['config']))
        model.load_state_dict(ckpt['state_dict'])
        model.eval()
        report[name] = {'params_M': round(sum(p.numel() for p in model.parameters()) / 1e6, 2)}
        for threads in (default, 1):
            torch.set_num_threads(threads)
            for p in sets['vivos_test_200'][:10] + sets['football_test_59'][:3]:
                run(model, p)  # warm-up (short + long clips)
            for set_name, paths in sets.items():
                times = [run(model, p) for p in paths]
                proc, audio = sum(t for t, _ in times), sum(d for _, d in times)
                per = sorted(t / d for t, d in times)
                report[name][f'{set_name}_threads{threads}'] = {'clips': len(times), 'audio_s': round(audio, 1), 'rtf': proc / audio,
                                                               'rtf_p95': per[int(.95 * len(per))], 'mean_clip_s': statistics.mean(t for t, _ in times)}
                print(name, set_name, threads, json.dumps(report[name][f'{set_name}_threads{threads}']), flush=True)
    Path(sys.argv[1]).write_text(json.dumps(report, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
