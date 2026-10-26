"""Build a new private supplement; reuse frozen VIVOS/FLEURS audio datasets."""
import copy
import hashlib
import json
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    repo = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo / 'ai-core'))
    from ai_core.scripts.prepare_asr_robust import sha
    from ai_core.scripts.finetune_asr_robust import data_identity, validate_recipe, RobustASRDataset
    from ai_core.training.datasets import CharVocab
    from ai_core.training.checkpoint import load_checkpoint

    old = Path('D:/data_training_ai/asr_robust/kaggle_dataset')
    english = Path('D:/data_training_ai/asr_english_v1_20261020')
    source = Path('D:/data_training_ai/asr_robust/outputs-v2/asr_robust_run/asr_ctc/best.pt')
    base = Path('D:/data_training_ai/asr_three_source_v1_20261020')
    data = base / 'kaggle_dataset'
    assert not data.exists(), 'refusing to overwrite packet'
    preflight = json.loads((english / 'preflight.json').read_text(encoding='utf-8'))
    guard = preflight['protected_hashes']
    assert all(sha(path) == digest for path, digest in guard.items())
    assert all(sha(english / 'prepared' / path) == digest for path, digest in preflight['prepared_files'].items())
    original = json.loads((old / 'asr_robust_manifest.json').read_text(encoding='utf-8'))
    payload = copy.deepcopy(original)
    payload['meta'].update(source_checkpoint_sha256=sha(source),
                           previous_asr_manifest_sha256=sha(old / 'asr_robust_manifest.json'),
                           english_manifest_sha256=sha(english / 'prepared/english_manifest.json'))
    assert sha(old / 'fleurs_audio.zip') == original['meta']['fleurs_archive_sha256']
    vivos = Path('D:/data_training_ai/kaggle_vivos_ds/vivos_waves.zip')
    assert sha(vivos) == original['meta']['vivos_archive_sha256']
    with zipfile.ZipFile(vivos) as archive:
        for row in payload['items']:
            if row['extra']['source'] == 'vivos':
                with archive.open(row['path']) as audio:
                    row['extra']['audio_sha256'] = hashlib.file_digest(audio, 'sha256').hexdigest()
    english_rows = json.loads((english / 'prepared/english_manifest.json').read_text(encoding='utf-8'))['items']
    data.mkdir(parents=True)
    with zipfile.ZipFile(data / 'english_audio.zip', 'x', compression=zipfile.ZIP_STORED) as archive:
        for row in english_rows:
            path = Path(row['path'])
            assert sha(path) == row['extra']['audio_sha256']
            relative = 'english_audio/' + path.relative_to(english / 'prepared/audio').as_posix()
            archive.write(path, relative)
            row['path'] = relative
    payload['items'].extend(english_rows)
    payload['meta']['english_archive_sha256'] = sha(data / 'english_audio.zip')
    write(data / 'asr_three_source_manifest.json', payload)
    shutil.copy2(source, data / 'source_asr.pt')
    shutil.copy2(old / 'robust_vocab.json', data / 'robust_vocab.json')
    vocab = CharVocab(json.loads((data / 'robust_vocab.json').read_text(encoding='utf-8'))['chars'])
    saved = load_checkpoint(str(data / 'source_asr.pt'))
    assert vocab.size == 133 and vocab.itos == (saved.get('char_vocab') or saved['metadata']['char_vocab'])
    assert sha(data / 'source_asr.pt') == preflight['candidate_checkpoint_sha256']
    recipe = {'id': 'asr-three-source-v1', 'seed': 1337, 'steps': 2000, 'eval_every': 500,
              'sampling_probabilities': {'vivos': .4, 'fleurs': .4, 'minilibrispeech': .2},
              'initial_checkpoint_sha256': sha(data / 'source_asr.pt'),
              'vocab_sha256': sha(data / 'robust_vocab.json'),
              'manifest_sha256': sha(data / 'asr_three_source_manifest.json'),
              'data_identity_sha256': data_identity(payload),
              'selection': 'all-domain-wer-cer-nonregression-and-english-wer-improvement'}
    validate_recipe(recipe, payload, sha(data / 'robust_vocab.json'), sha(data / 'source_asr.pt'), 2000)
    train = RobustASRDataset(str(data / 'asr_three_source_manifest.json'), 'train', vocab, augment=True)
    assert len(train) == 15076 and len(train.excluded) == 4
    assert all(r['path'].startswith('vivos_waves/') for r in train.excluded)
    # Prove every original label/split/group/metadata is retained, except the new audio hash.
    for before, after in zip(original['items'], payload['items']):
        retained = copy.deepcopy(after)
        if before['extra']['source'] == 'vivos':
            retained['extra'].pop('audio_sha256')
        assert retained == before
    write(data / 'recipe.json', recipe)
    files = {}
    with zipfile.ZipFile(data / 'ai_core.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((repo / 'ai-core/ai_core').rglob('*.py')):
            relative = path.relative_to(repo / 'ai-core').as_posix()
            files[relative] = sha(path)
            archive.write(path, relative)
    write(data / 'code_manifest.json', {'archive_sha256': sha(data / 'ai_core.zip'), 'files': files})
    write(data / 'dataset-metadata.json', {'title': 'ASR three-source private supplement v1',
        'id': 'traininghighlight/asr-three-source-v1', 'isPrivate': True, 'licenses': [{'name': 'other'}]})
    kernel = Path(__file__).parent
    shutil.copy2(repo / 'dist/kaggle/kernel-asr-robust/run_asr_robust.py', kernel / 'run_asr_three_source.py')
    write(kernel / 'kernel-metadata.json', {'id': 'traininghighlight/asr-three-source-guarded-v1',
        'title': 'ASR three-source guarded v1', 'code_file': 'run_asr_three_source.py',
        'language': 'python', 'kernel_type': 'script', 'is_private': True, 'enable_gpu': True,
        'enable_internet': False, 'dataset_sources': ['traininghighlight/asr-three-source-v1',
            'traininghighlight/asr-robust-human', 'traininghighlight/vivos-asr'],
        'competition_sources': [], 'kernel_sources': []})
    assert all(sha(path) == digest for path, digest in guard.items())
    statistics = {}
    for domain in recipe['sampling_probabilities']:
        for split in ('train', 'val', 'test'):
            rows = [r for r in payload['items'] if r['extra']['source'] == domain and r['split'] == split]
            statistics[domain + '_' + split] = {'examples': len(rows),
                'hours': sum(r['extra']['num_samples'] for r in rows) / 16000 / 3600}
    report = {'status': 'PACKED_NOT_UPLOADED_OR_TRAINED', 'packet': str(data), 'recipe': recipe,
              'statistics': statistics, 'ctc_retained_training': len(train), 'exclusions': train.excluded,
              'source_sampling_counts': dict(Counter(i.extra['source'] for i in train.items)),
              'packet_hashes': {p.name: sha(p) for p in sorted(data.iterdir()) if p.is_file()},
              'runner_sha256': sha(kernel / 'run_asr_three_source.py'),
              'protected_hashes': guard, 'old_references_and_splits_unchanged': True,
              'licenses': {'vivos': 'CC-BY-NC-SA-4.0', 'fleurs': 'CC-BY-4.0', 'minilibrispeech': 'CC-BY-4.0'},
              'limitations': ['Read English is not verified Vietnamese-English/legal-domain gold.',
                              'This packet reuses two existing private audio datasets; no public redistribution.',
                              'No remote dataset/kernel/API/GPU/quality check performed.']}
    write(base / 'preflight.json', report)
    write(repo / 'data/manifests/asr_three_source_preparation.json', report)
    print(json.dumps({k: report[k] for k in ['status', 'packet', 'statistics', 'source_sampling_counts']}, indent=2))


if __name__ == '__main__':
    main()
