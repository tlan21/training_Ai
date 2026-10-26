"""Keep original CC YouTube media on D:, freeze 30 clips, run own ASR -> MiniGPT."""

import csv
import datetime
import hashlib
import html
import json
import shutil
import subprocess
import time
import urllib.request
import wave
import zipfile
from pathlib import Path

from yt_dlp import YoutubeDL

from prepare_human_pilot import API, EXPECTED, ROOT

OUT = Path('D:/data_training_ai/minigpt_real_video_20261015')
PACKET = OUT / 'evaluation'
IDS = ['UZH4d1_NlI8', 'ObICsjyzHhU', 'y9_TESYEbmA', 'yAu3Zc3UNxQ',
       'oA0w-t5xVgg', 'QwKr8x7kfuo', 'TvUBN0XbMBA', 'JgqIdGgo948',
       'qc1mZSHcvB0', 'uV0sdwHCBtw']
MANIFEST = ROOT / 'data/manifests/minigpt_real_video.json'


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def load(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                            capture_output=True, check=True, encoding='utf-8')
    return json.loads(result.stdout)


def download():
    raw = OUT / 'raw/youtube'
    raw.mkdir(parents=True, exist_ok=True)
    sources = load(OUT / 'sources.json', [])
    for video_id in IDS:
        existing = next((s for s in sources if s['video_id'] == video_id), None)
        if existing:
            assert sha(OUT / existing['file']) == existing['sha256'], 'original media changed'
            continue
        url = 'https://www.youtube.com/watch?v=' + video_id
        options = {'quiet': True, 'noprogress': True, 'js_runtimes': {'node': {}},
                   'format': 'bv[height<=480][vcodec^=avc1][protocol=https]+ba[ext=m4a][protocol=https]/b[height<=480][protocol=https]',
                   'merge_output_format': 'mp4', 'outtmpl': str(raw / '%(id)s.%(ext)s'),
                   'retries': 3, 'fragment_retries': 3, 'socket_timeout': 30, 'writeinfojson': True,
                   'writesubtitles': False, 'writeautomaticsub': False, 'noplaylist': True}
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)
            assert info['id'] == video_id and 'Creative Commons' in (info.get('license') or ''), 'CC license required'
            assert info.get('language', '').startswith('vi') and info['duration'] >= 300, 'Vietnamese source >=300s required'
            downloader.process_info(info)
        path = raw / (video_id + '.mp4')
        metadata = probe(path)
        assert {'video', 'audio'} <= {s['codec_type'] for s in metadata['streams']}, 'audio and video required'
        sources.append({'video_id': video_id, 'url': url, 'title': info['title'], 'channel': info['channel'],
                        'channel_id': info['channel_id'], 'license': info['license'],
                        'license_url': 'https://support.google.com/youtube/answer/2797468',
                        'license_version': 'Unspecified in video metadata; preserve exact YouTube license label.',
                        'upload_date': info.get('upload_date'), 'language': info['language'],
                        'duration_seconds': float(metadata['format']['duration']),
                        'downloaded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        'file': path.relative_to(OUT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size,
                        'formats': info.get('format_id'), 'height': info.get('height'),
                        'preservation': 'Complete selected YouTube streams, muxed without re-encoding; original retained.'})
        save(OUT / 'sources.json', sources)
        print(f'Downloaded {len(sources)}/10: {video_id}', flush=True)
    assert [s['video_id'] for s in sources] == IDS
    return sources


def main():
    assert sha(ROOT / 'ai-core/checkpoints/minigpt/best.pt') == EXPECTED, 'MiniGPT checkpoint changed'
    asr_sha = sha(ROOT / 'ai-core/checkpoints/asr_ctc/best.pt')
    key = next(line.partition('=')[2].strip().strip('"\'') for line in (ROOT / '.env').read_text().splitlines()
               if line.strip().startswith('AI_SERVICE_KEY='))

    def request(path, data=None):
        req = urllib.request.Request(API + path, data=json.dumps(data).encode() if data is not None else None,
                                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        with urllib.request.urlopen(req, timeout=600) as response:
            return json.load(response)

    health = request('/health')
    assert not health['stub_mode'] and not health['degraded'] and len(health['models_loaded']) == 6
    sources = download()
    selection = {'protocol': '10 preselected Vietnamese CC videos; fixed offsets 60/150/240s, 60s each; no model-based selection.',
                 'minigpt_checkpoint_sha256': EXPECTED, 'asr_checkpoint_sha256': asr_sha,
                 'sources_sha256': sha(OUT / 'sources.json'), 'samples': []}
    for source in sources:
        for start in [60, 150, 240]:
            selection['samples'].append({'sample_id': f'sample_{len(selection["samples"]) + 1:02}',
                                         'video_id': source['video_id'], 'start_seconds': start, 'duration_seconds': 60})
    frozen = OUT / 'selection.json'
    if frozen.exists():
        assert load(frozen, {}) == selection, 'refusing to change frozen source/model selection'
    else:
        save(frozen, selection)
    for directory in ['audio', 'video']:
        (PACKET / directory).mkdir(parents=True, exist_ok=True)
    for sample in selection['samples']:
        source = next(s for s in sources if s['video_id'] == sample['video_id'])
        audio = PACKET / 'audio' / (sample['sample_id'] + '.wav')
        video = PACKET / 'video' / (sample['sample_id'] + '.mp4')
        if not audio.exists() or not video.exists():
            # Seeking after input makes each evaluation clip start at the frozen timestamp.
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(OUT / source['file']),
                            '-ss', str(sample['start_seconds']), '-t', '60', '-map', '0:v:0', '-map', '0:a:0',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-c:a', 'aac', '-movflags', '+faststart', str(video)], check=True)
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(OUT / source['file']),
                            '-ss', str(sample['start_seconds']), '-t', '60', '-vn', '-ac', '1', '-ar', '16000',
                            '-c:a', 'pcm_s16le', str(audio)], check=True)
        with wave.open(str(audio)) as wav:
            assert wav.getnchannels() == 1 and wav.getframerate() == 16000
            assert abs(wav.getnframes() / wav.getframerate() - 60) < .1
    compose = ['docker', 'compose', '--env-file', '.env', '-f', 'docker-compose.yml']
    subprocess.run(compose + ['exec', '-T', 'inference-service', 'mkdir', '-p', '/tmp/minigpt-real-eval'], cwd=ROOT, check=True)
    subprocess.run(compose + ['cp', str(PACKET / 'audio') + '/.', 'inference-service:/tmp/minigpt-real-eval/'], cwd=ROOT, check=True)
    rows = load(PACKET / 'samples.json', [])
    assert [r['sample_id'] for r in rows] == [s['sample_id'] for s in selection['samples'][:len(rows)]]
    for sample in selection['samples'][len(rows):]:
        source = next(s for s in sources if s['video_id'] == sample['video_id'])
        started = time.monotonic()
        asr = request('/v1/asr/completions', {'audio_url': '/tmp/minigpt-real-eval/' + sample['sample_id'] + '.wav', 'language': 'vi'})
        summary = request('/v1/completions', {'prompt': asr['full_transcript'], 'max_tokens': 96, 'temperature': 0})
        row = dict(sample, source_url=source['url'], title=source['title'], channel=source['channel'],
                   source_sha256=source['sha256'], audio='audio/' + sample['sample_id'] + '.wav',
                   video='video/' + sample['sample_id'] + '.mp4', asr=asr, summary=summary['choices'][0]['text'],
                   elapsed_seconds=time.monotonic() - started, request_temperature=0)
        row['audio_sha256'], row['video_sha256'] = sha(PACKET / row['audio']), sha(PACKET / row['video'])
        rows.append(row)
        save(PACKET / 'samples.json', rows)
        print(f'{len(rows)}/30 real ASR chars={len(asr["full_transcript"])}, summary chars={len(row["summary"])}', flush=True)
    assert len(rows) == 30
    for row in rows:
        assert sha(PACKET / row['audio']) == row['audio_sha256'] and sha(PACKET / row['video']) == row['video_sha256']
    for rater in range(1, 4):
        path = PACKET / f'ratings_rater_{rater}.csv'
        if not path.exists():
            with path.open('w', encoding='utf-8-sig', newline='') as target:
                writer = csv.writer(target)
                writer.writerow(['sample_id', 'overall_score_1_to_5', 'notes'])
                writer.writerows((r['sample_id'], '', '') for r in rows)
    esc = html.escape
    cards = []
    for row in rows:
        cards.append(f'<article><h2>{row["sample_id"]} — {esc(row["title"])}</h2>'
                     f'<p>{esc(row["channel"])} · <a href="{esc(row["source_url"])}">YouTube gốc</a> · {row["start_seconds"]}–{row["start_seconds"]+60}s</p>'
                     f'<video controls preload="none" src="{row["video"]}"></video>'
                     f'<p><b>ASR thật:</b> {esc(row["asr"]["full_transcript"])}</p><p><b>MiniGPT:</b> {esc(row["summary"])}</p></article>')
    instructions = '''# Chấm 30 summary từ video YouTube tiếng Việt thực tế

10 video nguồn ×3 đoạn không chồng lấn ×60 giây =30 phút. Nguồn gốc đầy đủ được giữ tại ../raw/youtube;
URL/channel/license/hash tại sources.json. CC BY theo metadata YouTube; không tải phụ đề/pseudo-label.
Đây là tập đánh giá, KHÔNG đưa vào training hoặc chọn checkpoint theo kết quả tập này.
Các nguồn có thể đã dùng cho ViT; đây không phải test unseen cho toàn bộ6 model.

Mở review.html, nghe/xem video. Chấm summary theo nội dung thực sự được nói, gồm lỗi dây chuyền ASR.
Không có transcript/reference do người tạo; ASR không phải ground truth. Không dùng model khác để chấm.
Ba người chấm độc lập, mỗi người điền một ratings_rater_N.csv, không xem điểm nhau.
1: sai ý/không output;2: sai nhiều/phải viết lại;3: có ý chính nhưng cần sửa đáng kể;
4: đúng ý/chỉnh nhẹ;5: chính xác/gọn/rõ/không bịa. Điền số nguyên1–5, giữ sample_id.
Chỉ tính mean khi đủ90 điểm thật; mean>=3/5 là ngưỡng. Điểm hiện để trống.

Sau khi điền đủ3 CSV, chạy từ E:/traning_ai:
.venv/Scripts/python.exe dist/kaggle/kernel-minigpt-news/score_human_pilot.py --manifest data/manifests/minigpt_real_video.json
'''
    (PACKET / 'README.md').write_text(instructions, encoding='utf-8')
    shutil.copy2(OUT / 'sources.json', PACKET / 'sources.json')
    shutil.copy2(frozen, PACKET / 'selection.json')
    (PACKET / 'review.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>30 video ASR → MiniGPT</title>'
                                      '<style>body{font:17px system-ui;max-width:900px;margin:32px auto;padding:16px}article{border-top:1px solid #bbb;padding:20px 0}p{line-height:1.6}video{width:100%;max-height:480px}</style>'
                                      '<h1>30 mẫu video thật: ASR → MiniGPT</h1><p>Chấm theo video gốc, ASR không phải ground truth. Ba người dùng3 CSV riêng; xem README.md.</p>' + ''.join(cards) + '</html>', encoding='utf-8')
    archive_path = OUT / 'minigpt_real_video_evaluation.zip'
    if not archive_path.exists():
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(PACKET.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(PACKET))
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
    manifest = {'date': '2026-10-15', 'status': 'REAL VIDEO PACKET READY — HUMAN RATINGS PENDING',
                'evaluation_kind': 'real_video', 'packet': str(PACKET), 'originals': str(OUT / 'raw/youtube'),
                'videos': 10, 'channels': len({s['channel_id'] for s in sources}), 'samples': 30, 'duration_seconds': 1800,
                'checkpoint_sha256': EXPECTED, 'asr_checkpoint_sha256': asr_sha,
                'samples_sha256': sha(PACKET / 'samples.json'), 'sources_sha256': sha(OUT / 'sources.json'),
                'selection_sha256': sha(frozen), 'archive': str(archive_path), 'archive_sha256': sha(archive_path),
                'empty_asr': sum(not r['asr']['full_transcript'] for r in rows), 'empty_summary': sum(not r['summary'] for r in rows),
                'results_file': 'docs/T1.6_real_video_human_results.json', 'human_ratings': 'UNMEASURED — blank sheets; never automatically assigned'}
    save(MANIFEST, manifest)
    save(PACKET / 'manifest.json', manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
