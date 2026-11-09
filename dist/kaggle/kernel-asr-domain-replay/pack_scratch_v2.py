"""AI-29 session 3: add empty-target NON-SPEECH clips (music/crowd) to the scratch union packet so the ASR learns to stay silent.

Sources (user-screened 2026-11-04: "4, 5(vol 2 chỉ có nhạc), 6, 10(vol 2 chỉ có nhạc), 11, 14, 15 (vol 2 chỉ có nhạc), 19 chỉ có nhạc"):
round-2 match videos 4, 6, 11, 14, 19 (no commentary) in full, the second half of 5, 10, 15 (music only), plus creator subtitle cues that are
bracketed non-speech tags ("[âm nhạc]"). 15 s windows, <= 40 per video; video 19 is the non-speech validation set. Never trains.
"""
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

from pack import write

ROOT = Path('D:/data_training_ai/football_asr_sources')
WIN, EDGE, CAP = 15.0, 10.0, 40
NO_COMMENTARY, SECOND_HALF_MUSIC, VAL_VIDEO = {4, 6, 11, 14, 19}, {5, 10, 15}, 19


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cut(src, start, dur, dst):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-ss', f'{start:.3f}', '-i', str(src), '-t', f'{dur:.3f}',
                    '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(dst)], check=True)


def bracket_cues(vtt):
    out = []
    for block in vtt.read_text(encoding='utf-8').split('\n\n'):
        lines = block.split('\n')
        for k, line in enumerate(lines):
            m = re.match(r'(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)', line)
            if m:
                text = ' '.join(lines[k + 1:])
                a = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
                b = int(m[4]) * 3600 + int(m[5]) * 60 + float(m[6])
                if re.fullmatch(r'\s*\[[^\]]*\]\s*', text) and b - a >= 2:
                    out.append((a, b))
                break
    return out


def main():
    import soundfile as sf
    repo = Path(__file__).resolve().parents[3]
    v1 = Path('D:/data_training_ai/asr_scratch_v1_20261106/kaggle_dataset')
    base = Path('D:/data_training_ai/asr_scratch_v2_20261109')
    data, clips = base / 'kaggle_dataset', base / 'clips'
    assert not base.exists(), 'refusing to overwrite experiment'
    clips.mkdir(parents=True)
    data.mkdir()
    items, report = [], Counter()

    def add(src, start, dur, video_id, url, split, origin):
        wav = clips / f'ns_{video_id}_{int(start * 100):07d}.wav'
        cut(src, start, dur, wav)
        items.append({'path': 'nonspeech_audio/' + wav.name, 'label': 'vi', 'split': split, 'group': 'ns_' + video_id,
                      'extra': {'source': 'nonspeech', 'transcript': '', 'audio_sha256': sha(wav), 'num_samples': sf.info(str(wav)).frames,
                                'video_id': video_id, 'source_url': url, 'start_seconds': round(start, 3),
                                'license': 'CC BY (YouTube Creative Commons)', 'label_origin': origin}})
        report[f'{origin}_{split}'] += 1

    for idx, s in enumerate(json.loads((ROOT / 'sources2.json').read_text(encoding='utf-8'))['sources'], 1):
        if idx not in NO_COMMENTARY | SECOND_HALF_MUSIC:
            continue
        start = EDGE if idx in NO_COMMENTARY else s['duration_s'] * .55
        end, n = s['duration_s'] - EDGE, 0
        while start + WIN <= end and n < CAP:
            add(ROOT / 'audio2' / s['file'], start, WIN, s['id'], s['url'], 'val' if idx == VAL_VIDEO else 'train', 'USER_SCREENED_NO_COMMENTARY')
            start, n = start + WIN, n + 1
    for s in json.loads((ROOT / 'creator_subs/sources.json').read_text(encoding='utf-8')):
        for a, b in bracket_cues(ROOT / 'creator_subs' / s['vtt'])[:CAP]:
            add(ROOT / 'creator_subs' / s['audio'], a, min(b - a, WIN), s['id'], s['url'], 'train', 'CREATOR_BRACKET_NONSPEECH')
    with zipfile.ZipFile(data / 'nonspeech_audio.pack', 'x', compression=zipfile.ZIP_STORED) as archive:
        for item in items:
            archive.write(clips / Path(item['path']).name, item['path'])
    payload = json.loads((v1 / 'scratch_manifest.json').read_text(encoding='utf-8'))
    payload['items'] += items
    payload['meta'].update(nonspeech_archive_sha256=sha(data / 'nonspeech_audio.pack'), task='AI-29 scratch ASR union + non-speech (session 3)',
                           scratch_v1_manifest_sha256=sha(v1 / 'scratch_manifest.json'))
    write(data / 'scratch_manifest_v2.json', payload)
    shutil.copy2(v1 / 'robust_vocab.json', data / 'robust_vocab.json')
    shutil.copy2(Path(__file__).parent / 'run_asr_domain_replay.py', data / 'asr_stage.py')
    with zipfile.ZipFile(data / 'ai_core.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((repo / 'ai-core/ai_core').rglob('*.py')):
            archive.write(path, path.relative_to(repo / 'ai-core').as_posix())
        for path in sorted((repo / 'ai-core/ai_core/training/configs').glob('*.yaml')):
            archive.write(path, path.relative_to(repo / 'ai-core').as_posix())
    write(data / 'dataset-metadata.json', {'title': 'ASR scratch union nonspeech private supplement v2',
        'id': 'traininghighlight/asr-scratch-v2', 'isPrivate': True, 'licenses': [{'name': 'other'}]})
    out = {'status': 'PACKED_NOT_UPLOADED_OR_TRAINED', 'nonspeech': dict(report),
           'nonspeech_minutes': round(sum(i['extra']['num_samples'] for i in items) / 16000 / 60, 1),
           'items_total': len(payload['items']), 'manifest_sha256': sha(data / 'scratch_manifest_v2.json')}
    write(base / 'preflight.json', out)
    write(repo / 'data/manifests/asr_scratch_v2_preparation.json', out)
    print('PACKED', json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
