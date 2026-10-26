"""Frozen VIVOS + human-read FLEURS vi; no pretrained transcripts or YouTube test data."""

import hashlib
import gc
import io
import json
import shutil
import unicodedata
import wave
import zipfile
from pathlib import Path


def normalize(text):
    value = ' '.join(unicodedata.normalize('NFC', text).upper().split())
    if not value:
        raise ValueError('empty human transcript')
    return value


def extend_chars(original, training_texts):
    assert len(original) == len(set(original)) and all(len(c) == 1 for c in original)
    additions = sorted(set(''.join(training_texts)) - set(original))
    return list(original) + additions


def assert_disjoint(items):
    groups = {split: {i['group'] for i in items if i['split'] == split} for split in ['train', 'val', 'test']}
    for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]:
        assert not groups[a] & groups[b], f'{a}/{b} groups overlap'
    assert all(groups.values()), 'empty split'


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    import numpy as np
    import pyarrow.parquet as pq
    import soundfile as sf

    repo = Path(__file__).resolve().parents[3]
    base = Path('D:/data_training_ai/asr_robust')
    raw = base / 'raw/fleurs_vi'
    out = base / 'kaggle_dataset'
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / 'asr_robust_manifest.json'
    if manifest_path.exists():
        raise SystemExit('Frozen prepared dataset exists; refusing to replace it')
    sources = json.loads((raw / 'source.json').read_text(encoding='utf-8'))
    old_root = Path('D:/data_training_ai/kaggle_vivos_ds')
    vivos = json.loads((old_root / 'vivos.json').read_text(encoding='utf-8'))
    original_chars = json.loads((old_root / 'vivos_vocab.json').read_text(encoding='utf-8'))['chars']
    items = []
    with zipfile.ZipFile(old_root / 'vivos_waves.zip') as archive:
        for source in vivos['items']:
            row = dict(source, group='vivos:' + source['group'], extra=dict(source['extra'], source='vivos'))
            with archive.open(source['path']) as stream, wave.open(stream) as audio:
                assert audio.getframerate() == 16000 and audio.getnchannels() == 1
                row['extra']['num_samples'] = audio.getnframes()
            assert normalize(row['extra']['transcript']) == row['extra']['transcript']
            items.append(row)
    print('VIVOS original splits retained:', len(items), flush=True)
    fingerprints = {split: set() for split in ['train', 'val', 'test']}
    for official, split in [('train', 'train'), ('validation', 'val'), ('test', 'test')]:
        path = raw / (official + '.parquet')
        assert sha(path) == sources[official]['sha256'], 'raw source changed'
        folder = out / 'fleurs_audio' / split
        folder.mkdir(parents=True, exist_ok=True)
        count = 0
        parquet = pq.ParquetFile(path, memory_map=True, pre_buffer=False)
        for batch in parquet.iter_batches(batch_size=1, use_threads=False):
            for record in batch.to_pylist():
                encoded = record['audio']['bytes']
                signal, rate = sf.read(io.BytesIO(encoded), dtype='float32')
                assert rate == 16000 and signal.ndim == 1 and len(signal) == record['num_samples']
                assert np.isfinite(signal).all() and len(signal) >= 400
                destination = folder / f'{count:05}.flac'
                if not destination.exists():
                    sf.write(destination, signal, 16000, subtype='PCM_16')
                info = sf.info(destination)
                assert info.samplerate == 16000 and info.channels == 1 and info.frames == len(signal)
                fingerprint = hashlib.sha256(encoded).hexdigest()
                fingerprints[split].add(fingerprint)
                text = normalize(record['transcription'])
                items.append({'path': destination.relative_to(out).as_posix(), 'label': 'vi', 'split': split,
                              'group': 'fleurs:' + str(record['id']),
                              'extra': {'source': 'fleurs', 'transcript': text, 'raw_transcription': record['raw_transcription'],
                                        'source_row': count, 'source_id': record['id'], 'source_audio_sha256': fingerprint,
                                        'audio_sha256': sha(destination), 'num_samples': len(signal),
                                        'official_split': official, 'source_path': record['audio']['path']}})
                count += 1
            if count % 256 == 0:
                print(f'FLEURS {official}: {count} recordings', flush=True)
                gc.collect()
            del batch, record, encoded, signal
        print(f'FLEURS {official} done: {count}', flush=True)
    assert_disjoint(items)
    for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]:
        assert not fingerprints[a] & fingerprints[b], 'audio leakage across splits'
    chars = extend_chars(original_chars, [r['extra']['transcript'] for r in items if r['split'] == 'train'])
    statistics = {}
    for source in ['vivos', 'fleurs']:
        for split in ['train', 'val', 'test']:
            selected = [r for r in items if r['extra']['source'] == source and r['split'] == split]
            statistics[source + '_' + split] = {'examples': len(selected),
                                                'hours': sum(r['extra']['num_samples'] for r in selected) / 16000 / 3600,
                                                'oov_characters': sorted(set(''.join(r['extra']['transcript'] for r in selected)) - set(chars))}
    initial = repo / 'ai-core/checkpoints/asr_ctc/best.pt'
    meta = {'seed': 1337, 'sr': 16000, 'source': sources, 'statistics': statistics,
            'source_checkpoint_sha256': sha(initial), 'vivos_manifest_sha256': sha(old_root / 'vivos.json'),
            'vivos_archive_sha256': sha(old_root / 'vivos_waves.zip'),
            'vivos_val_speakers': vivos['meta']['val_speakers'], 'original_n_chars': len(original_chars) + 1,
            'n_chars': len(chars) + 1, 'added_training_characters': chars[len(original_chars):],
            'label_provenance': 'VIVOS prompts + FLEURS human-translated prompts read by humans; upstream NFC/FST text normalization, not machine ASR.',
            'exclusions': 'No YouTube30, pretrained drafts, external weights/tokenizers or test-derived vocab additions.',
            'licenses': {'vivos': 'CC-BY-NC-SA-4.0', 'fleurs': 'CC-BY-4.0'}}
    (out / 'robust_vocab.json').write_text(json.dumps({'chars': chars}, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copy2(initial, out / 'source_asr.pt')
    assert sha(out / 'source_asr.pt') == meta['source_checkpoint_sha256']
    with zipfile.ZipFile(out / 'fleurs_audio.zip', 'w', compression=zipfile.ZIP_STORED) as archive:
        for path in sorted((out / 'fleurs_audio').rglob('*.flac')):
            archive.write(path, path.relative_to(out))
    meta['fleurs_archive_sha256'] = sha(out / 'fleurs_audio.zip')
    manifest_path.write_text(json.dumps({'meta': meta, 'items': items}, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'dataset-metadata.json').write_text(json.dumps({'title': 'asr-robust-human',
        'id': 'traininghighlight/asr-robust-human', 'isPrivate': True, 'licenses': [{'name': 'other'}]}, indent=2), encoding='utf-8')
    # Only the archive is uploaded; preserve decoded files outside the upload folder.
    destination = base / 'processed/fleurs_audio'
    destination.parent.mkdir(exist_ok=True)
    assert not destination.exists() and (out / 'fleurs_audio').resolve().is_relative_to(base.resolve())
    assert destination.resolve().is_relative_to(base.resolve())
    (out / 'fleurs_audio').rename(destination)
    report = {'status': 'PREPARED — TRAINING NOT STARTED', 'dataset': str(out), 'manifest_sha256': sha(manifest_path), **meta}
    (repo / 'data/manifests/asr_robust_dataset.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(statistics, ensure_ascii=False, indent=2), flush=True)
    print('VOCAB', len(original_chars) + 1, '->', len(chars) + 1, 'train-only additions', ''.join(meta['added_training_characters']), flush=True)


if __name__ == '__main__':
    main()
