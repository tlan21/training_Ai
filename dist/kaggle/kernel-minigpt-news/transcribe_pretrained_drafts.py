"""User-authorized local pretrained drafts, isolated from human labels and project models."""

import csv
import gc
import hashlib
import html
import importlib.metadata
import json
import math
import time
import urllib.request
import wave
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('D:/data_training_ai/minigpt_real_video_20261015')
OUT = BASE / 'pretrained_drafts_3'
IDS = ['sample_01', 'sample_10', 'sample_28']
STATUS = 'PRETRAINED_DRAFT_UNVERIFIED'
OPTIONS = {'language': 'vi', 'task': 'transcribe', 'beam_size': 5, 'temperature': 0,
           'condition_on_previous_text': False, 'vad_filter': False}


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def timestamp(seconds):
    assert math.isfinite(seconds) and seconds >= 0
    hours, remainder = divmod(round(seconds * 1000), 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02},{millis:03}'


def srt(segments, duration=math.inf):
    assert all(0 <= s['start'] < min(s['end'], duration) and s['text'].strip() for s in segments)
    return '\n\n'.join(f'{i}\n{timestamp(s["start"])} --> {timestamp(min(s["end"], duration))}\n{s["text"].strip()}'
                         for i, s in enumerate(segments, 1)) + '\n'


def main():
    from faster_whisper import WhisperModel

    OUT.mkdir(exist_ok=True)
    manifest = json.loads((ROOT / 'data/manifests/minigpt_real_video.json').read_text(encoding='utf-8'))
    frozen = BASE / 'evaluation/samples.json'
    assert sha(frozen) == manifest['samples_sha256']
    samples = {r['sample_id']: r for r in json.loads(frozen.read_text(encoding='utf-8'))}
    refs = BASE / 'asr_ground_truth_30/references.csv'
    refs_hash = sha(refs)
    model_info = json.loads(Path('D:/data_training_ai/tools/asr_draft_model_manifest.json').read_text(encoding='utf-8'))
    model_dir = Path(model_info['path'])
    for file in model_info['files']:
        assert sha(model_dir / file['file']) == file['sha256'], 'pretrained model artifact changed'
    versions = {name: importlib.metadata.version(name) for name in ['faster-whisper', 'ctranslate2', 'av']}
    model = None
    records = []
    for sample_id in IDS:
        sample = samples[sample_id]
        audio = BASE / 'evaluation' / sample['audio']
        assert sha(audio) == sample['audio_sha256']
        result_path = OUT / (sample_id + '.json')
        if result_path.exists():
            record = json.loads(result_path.read_text(encoding='utf-8'))
            assert record['audio_sha256'] == sample['audio_sha256'] and record['model_revision'] == model_info['revision']
            assert record['decoding_options'] == OPTIONS and record['status'] == STATUS
        else:
            if model is None:
                print('Loading local multilingual model on CPU INT8...', flush=True)
                model = WhisperModel(str(model_dir), device='cpu', compute_type='int8', cpu_threads=4,
                                     num_workers=1, local_files_only=True)
            started = time.monotonic()
            with wave.open(str(audio)) as stream:
                duration = stream.getnframes() / stream.getframerate()
            generated, info = model.transcribe(str(audio), **OPTIONS)
            segments = []
            for segment in generated:
                segments.append(asdict(segment))
                print(f'{sample_id}: {segment.start:.2f}-{segment.end:.2f}s', flush=True)
            text = ' '.join(s['text'].strip() for s in segments).strip()
            assert text, f'{sample_id}: empty draft; do not replace with fabricated text'
            record = {'sample_id': sample_id, 'status': STATUS, 'human_verified': False,
                      'model_repo': model_info['model_repo'], 'model_revision': model_info['revision'],
                      'versions': versions, 'device': 'cpu', 'compute_type': 'int8', 'decoding_options': OPTIONS,
                      'audio': str(audio), 'audio_sha256': sample['audio_sha256'], 'duration_seconds': duration,
                      'source_url': sample['source_url'], 'source_start_seconds': sample['start_seconds'],
                      'language': info.language, 'language_probability': info.language_probability,
                      'draft_text': text, 'segments': segments, 'elapsed_seconds': time.monotonic() - started,
                      'project_asr': sample['asr']['full_transcript'], 'project_summary_from_asr': sample['summary'],
                      'authorization': 'User explicitly permitted local pretrained ASR drafts for these3samples only.',
                      'use': 'Draft for human review/diagnosis; not ground truth, training data or official WER/CER.'}
            save(result_path, record)
        (OUT / (sample_id + '.txt')).write_text(STATUS + '\n\n' + record['draft_text'] + '\n', encoding='utf-8')
        (OUT / (sample_id + '.srt')).write_text(srt(record['segments'], record['duration_seconds']), encoding='utf-8')
        records.append(record)
        print(f'COMPLETE {sample_id}: {len(record["draft_text"])} characters', flush=True)
    del model
    gc.collect()
    key = next(line.partition('=')[2].strip().strip('"\'') for line in (ROOT / '.env').read_text().splitlines()
               if line.strip().startswith('AI_SERVICE_KEY='))
    for record in records:
        if 'project_summary_from_draft' not in record:
            req = urllib.request.Request('http://127.0.0.1:8001/v1/completions',
                                         data=json.dumps({'prompt': record['draft_text'], 'max_tokens': 96, 'temperature': 0}).encode(),
                                         headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
            with urllib.request.urlopen(req, timeout=180) as response:
                output = json.load(response)
            record['project_summary_from_draft'] = output['choices'][0]['text']
            save(OUT / (record['sample_id'] + '.json'), record)
    with (OUT / 'drafts.csv').open('w', encoding='utf-8-sig', newline='') as target:
        writer = csv.writer(target)
        writer.writerow(['sample_id', 'pretrained_draft', 'status', 'human_verified'])
        writer.writerows((r['sample_id'], r['draft_text'], STATUS, 'false') for r in records)
    cards = []
    esc = html.escape
    for record in records:
        sid = record['sample_id']
        cards.append(f'<article><h2>{sid}</h2><video controls preload="none" src="../evaluation/video/{sid}.mp4"></video>'
                     f'<h3>Bản nháp pretrained — chưa kiểm chứng</h3><p>{esc(record["draft_text"])}</p>'
                     f'<p><a href="{sid}.srt">SRT</a> · <a href="{sid}.txt">TXT</a></p>'
                     f'<details><summary>Đối chiếu output model dự án</summary><h3>ASR dự án</h3><p>{esc(record["project_asr"])}</p>'
                     f'<h3>MiniGPT từ ASR dự án</h3><p>{esc(record["project_summary_from_asr"])}</p>'
                     f'<h3>MiniGPT từ bản nháp</h3><p>{esc(record["project_summary_from_draft"])}</p></details></article>')
    (OUT / 'review.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>3 bản nháp ASR</title>'
                                   '<style>body{font:17px system-ui;max-width:900px;margin:auto;padding:24px}p{line-height:1.6}video{width:100%;max-height:480px}article{border-top:1px solid #aaa;padding:24px 0}</style>'
                                   '<h1>3 bản nháp pretrained — cần người nghe kiểm chứng</h1><p>Đây không phải lời chuẩn hoặc kết quả model ASR dự án. Chưa dùng để train hay tính CER/WER chính thức.</p>'
                                   + ''.join(cards) + '</html>', encoding='utf-8')
    summary = {'status': 'DRAFTS COMPLETE — HUMAN VERIFICATION PENDING', 'sample_ids': IDS,
               'authorization': 'Explicit user exception: local pretrained ASR drafts only.',
               'model': model_info, 'versions': versions, 'decoding_options': OPTIONS, 'device': 'cpu', 'compute_type': 'int8',
               'packet': str(OUT), 'human_verified_samples': 0, 'official_video_wer': None, 'official_video_cer': None,
               'samples_sha256': manifest['samples_sha256'], 'human_references_sha256': refs_hash,
               'inference_seconds': sum(r['elapsed_seconds'] for r in records),
               'files': {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'manifest.json'}}
    assert sha(refs) == refs_hash and sha(frozen) == manifest['samples_sha256']
    assert len(records) == 3 and all(not r['human_verified'] for r in records)
    save(OUT / 'manifest.json', summary)
    save(ROOT / 'data/manifests/pretrained_asr_drafts_3.json', summary)
    print(json.dumps({'status': summary['status'], 'packet': str(OUT), 'inference_seconds': summary['inference_seconds']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
