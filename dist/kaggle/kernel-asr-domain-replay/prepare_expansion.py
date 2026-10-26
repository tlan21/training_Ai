"""Collect a small train-only candidate supplement; no transcripts, labels or training."""
import hashlib
import json
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('D:/data_training_ai/asr_domain_replay_v1_20261021')
OUT = Path('D:/data_training_ai/asr_domain_expansion_v2_20261022')
OLD = Path('D:/data_training_ai/minigpt_domain_v1_20261019')
FROZEN = Path('D:/data_training_ai/minigpt_real_video_20261015')
SOURCES = [('uvs5djEOuH4', 6, 'english_class'), ('DL_TeDUv_LI', 3, 'medical_terms'),
    ('mHatGR-AoLY', 7, 'engineering_terms'), ('_9FWeRZBOSQ', 6, 'university_terms'),
    ('TeE0V-91_OU', 8, 'technical_brand_terms'), ('YNlLf8-cFao', 6, 'names_brands_places'),
    ('-wJIxQwbjOM', 6, 'legal_identifiers'), ('Dh8IdZtdYfk', 8, 'legal_identifiers'),
    ('qlt8lkh_G5k', 10, 'legal_identifiers')]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def starts(duration, count):
    assert count > 0 and duration >= 20 * count + 10, 'insufficient nonoverlapping source audio'
    return [round(5 + (duration - 30) * i / max(1, count - 1), 3) for i in range(count)]


def check_source(info, forbidden_videos, forbidden_channels):
    assert info['id'] not in forbidden_videos and info['channel_id'] not in forbidden_channels, 'source leakage'
    assert 'Creative Commons' in (info.get('license') or ''), 'unverified reuse license'
    assert info.get('availability') not in ('private', 'premium_only', 'subscriber_only', 'needs_auth')


def main():
    from yt_dlp import YoutubeDL
    sys.path.insert(0, str(ROOT / 'ai-core'))
    from ai_core.training.datasets import ASRDataset, CharVocab
    assert not OUT.exists(), 'candidate packet already exists; never overwrite review work'
    run = json.loads((ROOT / 'data/manifests/asr_domain_replay_training.json').read_text(encoding='utf-8'))
    assert run['status'] == 'TRAINED_OUTPUT_VERIFIED_NOT_DEPLOYED'
    previous = json.loads((OLD / 'sources.json').read_text(encoding='utf-8'))
    frozen = json.loads((FROZEN / 'sources.json').read_text(encoding='utf-8'))
    forbidden_videos = {s['video_id'] for s in previous + frozen}
    forbidden_channels = {s['channel_id'] for s in previous + frozen}
    protected = {**run['protected_hashes'], str(OLD / 'sources.json'): sha(OLD / 'sources.json')}
    assert all(sha(p) == h for p, h in protected.items())
    OUT.mkdir()
    raw = OUT / 'raw/youtube'
    raw.mkdir(parents=True)
    sources, samples = [], []
    for vid, count, hint in SOURCES:
        options = {'quiet': True, 'no_warnings': True, 'noprogress': True, 'noplaylist': True,
            'socket_timeout': 20, 'retries': 1, 'fragment_retries': 1, 'js_runtimes': {'node': {}},
            'outtmpl': str(raw / '%(id)s.%(ext)s'), 'merge_output_format': 'mp4', 'writeinfojson': True,
            'writesubtitles': False, 'writeautomaticsub': False}
        language = 'en' if hint == 'english_class' else 'vi'
        video = 'bv[height<=144][vcodec^=avc1][protocol=https]'
        audio = 'ba[ext=m4a][protocol=https]'
        options['format'] = video + '+' + audio + '[language^=' + language + ']/' + video + '+' + audio
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info('https://www.youtube.com/watch?v=' + vid, download=False)
            check_source(info, forbidden_videos, forbidden_channels)
            assert info['channel_id'] not in {s['channel_id'] for s in sources}, 'one source per new channel'
            estimated = sum(f.get('filesize') or f.get('filesize_approx') or 10 * 1024**2 for f in info.get('requested_formats', [info]))
            # Reserve the complete60-clip WAV/preview budget plus1GiB; never delete old data to fit.
            assert shutil.disk_usage('D:/').free > 1024**3 + estimated + 60 * 1000000, 'insufficient storage reserve'
            selected_languages = [f.get('language') for f in info.get('requested_formats', []) if f.get('acodec') not in (None, 'none')]
            assert all(not x or x.startswith(language) for x in selected_languages), 'unexpected dubbed audio language'
            ydl.process_info(info)
        media = raw / (vid + '.mp4')
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(media)]))
        assert {'audio', 'video'} <= {s['codec_type'] for s in probe['streams']}
        duration = float(probe['format']['duration'])
        source = {'video_id': vid, 'url': info['webpage_url'], 'title': info['title'],
            'channel_id': info['channel_id'], 'channel': info['channel'], 'duration_seconds': duration,
            'license': info['license'], 'license_version': 'Unspecified by platform metadata; exact attribution retained',
            'upload_date': info.get('upload_date'), 'language_metadata': info.get('language'),
            'selected_audio_languages': selected_languages, 'speech_language_human_verified': False,
            'content_hint': hint, 'content_hint_verified': False, 'file': media.relative_to(OUT).as_posix(),
            'sha256': sha(media), 'bytes': media.stat().st_size, 'downloaded_at_unix': time.time()}
        sources.append(source)
        for i, start in enumerate(starts(duration, count), 1):
            samples.append({'sample_id': f'ext2_{vid}_{i}', 'video_id': vid, 'channel_id': info['channel_id'],
                'split': 'train', 'start_seconds': start, 'duration_seconds': 20, 'source_sha256': source['sha256'],
                'source_url': source['url'], 'content_hint': hint, 'content_hint_verified': False})
        print('SOURCE_DOWNLOADED', vid, source['bytes'], flush=True)
        save(OUT / 'source_receipt_{}.json'.format(len(sources)), source)
    assert len(sources) == 9 and len(samples) == 60
    save(OUT / 'sources.json', sources)
    known_pcm = set()
    for folder in (OLD / 'audio', FROZEN / 'evaluation/audio'):
        for path in folder.glob('*.wav'):
            with wave.open(str(path)) as audio:
                known_pcm.add(hashlib.sha256(audio.readframes(audio.getnframes())).hexdigest())
    for folder in ('audio', 'video'):
        (OUT / folder).mkdir()
    for row in samples:
        source = next(s for s in sources if s['video_id'] == row['video_id'])
        for kind, ext in [('audio', 'wav'), ('video', 'mp4')]:
            path = OUT / kind / (row['sample_id'] + '.' + ext)
            cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-threads', '2',
                   '-ss', str(row['start_seconds']), '-i', str(OUT / source['file']), '-t', '20']
            cmd += ['-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le'] if kind == 'audio' else [
                '-map', '0:v:0', '-map', '0:a:0', '-vf', 'fps=12', '-c:v', 'libx264', '-threads', '2',
                '-preset', 'veryfast', '-crf', '32', '-c:a', 'aac', '-b:a', '48k', '-movflags', '+faststart']
            subprocess.run(cmd + [str(path)], check=True)
            row[kind], row[kind + '_sha256'] = path.relative_to(OUT).as_posix(), sha(path)
        with wave.open(str(OUT / row['audio'])) as audio:
            assert audio.getnchannels() == 1 and audio.getframerate() == 16000 and audio.getnframes() == 320000
            pcm = audio.readframes(audio.getnframes())
        fingerprint = hashlib.sha256(pcm).hexdigest()
        assert fingerprint not in known_pcm and any(pcm), 'duplicate or empty candidate audio'
        known_pcm.add(fingerprint)
        row['pcm_sha256'] = fingerprint
    assert shutil.disk_usage('D:/').free > 1024**3
    save(OUT / 'samples.json', samples)
    labels = {'protocol': 'asr-training-supplement-v2', 'samples_sha256': sha(OUT / 'samples.json'),
        'annotator': '', 'training_ready': False, 'records': [{
            'sample_id': r['sample_id'], 'split': 'train', 'audio_sha256': r['audio_sha256'],
            'transcript': '', 'verified': False, 'draft_origin': 'NO_MACHINE_TRANSCRIPT_CREATED',
            'label_origin': None, 'language_verified': '', 'speaker_id': '', 'exclude_reason': ''} for r in samples]}
    save(OUT / 'labels_blank.json', labels)
    blank_manifest = {'meta': {'status': 'CANDIDATES_ONLY_NO_LABELS', 'training_ready': False}, 'items': [
        {'path': str(OUT / r['audio']), 'split': 'train', 'group': r['channel_id'],
         'extra': {'transcript': '', 'source': 'unverified_domain_expansion_candidate'}} for r in samples]}
    save(OUT / 'candidate_manifest_NOT_TRAINABLE.json', blank_manifest)
    vocab = CharVocab(json.loads((BASE / 'kaggle_dataset/robust_vocab.json').read_text(encoding='utf-8'))['chars'])
    try:
        ASRDataset(str(OUT / 'candidate_manifest_NOT_TRAINABLE.json'), 'train', vocab)
    except ValueError as error:
        assert 'empty ASR transcript' in str(error)
    else:
        raise AssertionError('blank candidates accepted for training')
    assert all(sha(p) == h for p, h in protected.items())
    report = {'status': 'TRAIN_ONLY_MEDIA_READY_NO_LABELS', 'directory': str(OUT), 'sources': 9, 'channels': 9,
        'clips': 60, 'candidate_minutes': 20, 'approved_labels': 0, 'training_ready': False,
        'source_bytes': sum(s['bytes'] for s in sources), 'forbidden_channels': sorted(forbidden_channels),
        'protected_hashes': protected, 'samples_sha256': sha(OUT / 'samples.json'),
        'sources_sha256': sha(OUT / 'sources.json'), 'labels_blank_sha256': sha(OUT / 'labels_blank.json'),
        'blank_training_rejected': True, 'exact_pcm_duplicates': 0, 'semantic_or_speaker_disjointness_verified': False,
        'content_hints_are_not_verified_speech_coverage': True, 'new_transcripts_created': 0,
        'training_started': False, 'checkpoint_deployed': False}
    save(OUT / 'preparation.json', report)
    save(ROOT / 'data/manifests/asr_domain_expansion_v2.json', report)
    print('MEDIA_READY_NO_LABELS', len(samples), 'CLIPS20MIN', flush=True)


if __name__ == '__main__':
    main()
