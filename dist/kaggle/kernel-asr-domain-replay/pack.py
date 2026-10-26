"""Prepare one bounded private domain/replay experiment; never submit or train."""
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
    sys.path[:0] = [str(repo / 'ai-core'), str(repo / 'dist/kaggle/kernel-minigpt-domain')]
    from ai_core.scripts.prepare_asr_robust import extend_chars, sha
    from ai_core.scripts.finetune_asr_robust import data_identity, validate_recipe, RobustASRDataset, DOMAIN_SOURCE
    from ai_core.training.datasets import CharVocab
    from ai_core.training.checkpoint import load_checkpoint
    from asr_gold import validate

    old = Path('D:/data_training_ai/asr_three_source_v1_20261020/kaggle_dataset')
    domain = Path('D:/data_training_ai/minigpt_domain_v1_20261019/asr_verbatim_v1')
    base = Path('D:/data_training_ai/asr_domain_replay_v1_20261021')
    data = base / 'kaggle_dataset'
    assert not base.exists(), 'refusing to overwrite experiment'
    intake = json.loads((repo / 'data/manifests/asr_verbatim_intake.json').read_text(encoding='utf-8'))
    assert intake['counts'] == {'train': 30, 'val': 10} and intake['pending'] == {'train': [], 'val': []}
    source_labels = domain / ('received_' + intake['source_labels_sha256'][:12]) / 'asr_verbatim_domain_v1.json'
    assert sha(source_labels) == intake['source_labels_sha256']
    packet = json.loads((domain / 'packet.json').read_text(encoding='utf-8'))
    approved, pending = validate(json.loads(source_labels.read_text(encoding='utf-8-sig')), packet)
    assert pending == {'train': [], 'val': []}
    frozen = domain / 'frozen_validation.json'
    references = [{'sample_id': r['sample_id'], 'audio_sha256': r['extra']['audio_sha256'],
                   'transcript': r['extra']['transcript']} for r in sorted(approved['val'], key=lambda r: r['sample_id'])]
    assert references == json.loads(frozen.read_text(encoding='utf-8'))
    reference_identity = hashlib.sha256(json.dumps(references, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    prep = json.loads((domain / 'preparation.json').read_text(encoding='utf-8'))
    guard = {**prep['protected_hashes'], str(source_labels): sha(source_labels), str(frozen): sha(frozen)}
    for name in ('asr_three_source_manifest.json', 'recipe.json', 'robust_vocab.json', 'source_asr.pt', 'ai_core.zip'):
        guard[str(old / name)] = sha(old / name)
    assert all(sha(p) == h for p, h in guard.items())
    original = json.loads((old / 'asr_three_source_manifest.json').read_text(encoding='utf-8'))
    payload = copy.deepcopy(original)
    source = old / 'source_asr.pt'
    assert sha(source) == 'd03ef0a962220618e90e5ff478a2fbab5ff35dd68deb539a4933eb7c15a4f3de'
    payload['meta'].update(source_checkpoint_sha256=sha(source),
        previous_three_source_manifest_sha256=sha(old / 'asr_three_source_manifest.json'),
        domain_review_sha256=sha(source_labels), frozen_validation_sha256=sha(frozen),
        domain_validation_identity_sha256=reference_identity,
        domain_label_origin='human_reviewed_external_asr', domain_final_test_available=False)
    old_chars = json.loads((old / 'robust_vocab.json').read_text(encoding='utf-8'))['chars']
    chars = extend_chars(old_chars, [r['extra']['transcript'] for r in approved['train']])
    vocab = CharVocab(chars)
    assert vocab.size == 134 and chars[:-1] == old_chars and chars[-1] == '?'
    saved = load_checkpoint(str(source))
    assert (saved.get('char_vocab') or saved['metadata']['char_vocab']) == ['<blank>'] + old_chars
    data.mkdir(parents=True)
    with zipfile.ZipFile(data / 'domain_audio.zip', 'x', compression=zipfile.ZIP_STORED) as archive:
        for split in ('train', 'val'):
            for row in approved[split]:
                audio = Path(row['path'])
                assert sha(audio) == row['extra']['audio_sha256']
                import soundfile as sf
                info = sf.info(str(audio))
                assert info.samplerate == 16000 and info.channels == 1 and info.frames == 480000
                item = {k: copy.deepcopy(v) for k, v in row.items() if k != 'sample_id'}
                item['path'] = 'domain_audio/' + audio.name
                item['extra']['num_samples'] = info.frames
                assert item['extra']['source'] == DOMAIN_SOURCE
                archive.write(audio, item['path'])
                payload['items'].append(item)
    assert payload['items'][:len(original['items'])] == original['items']
    payload['meta']['domain_archive_sha256'] = sha(data / 'domain_audio.zip')
    write(data / 'asr_domain_manifest.json', payload)
    write(data / 'robust_vocab.json', {'chars': chars})
    shutil.copy2(source, data / 'source_asr.pt')
    shutil.copy2(frozen, data / 'frozen_validation.json')
    recipe = {'id': 'asr-domain-replay-v1', 'seed': 1337, 'steps': 500, 'eval_every': 100,
        'sampling_probabilities': {'vivos': .4, 'fleurs': .3, 'minilibrispeech': .2, DOMAIN_SOURCE: .1},
        'initial_checkpoint_sha256': sha(source), 'vocab_sha256': sha(data / 'robust_vocab.json'),
        'manifest_sha256': sha(data / 'asr_domain_manifest.json'), 'data_identity_sha256': data_identity(payload),
        'frozen_validation_sha256': sha(frozen),
        'domain_validation_identity_sha256': reference_identity,
        'selection': 'all-domain-wer-cer-nonregression-and-domain-wer-cer-improvement'}
    validate_recipe(recipe, payload, sha(data / 'robust_vocab.json'), sha(source), 500)
    write(data / 'recipe.json', recipe)
    training = RobustASRDataset(str(data / 'asr_domain_manifest.json'), 'train', vocab, augment=True)
    assert len(training) == 15106 and len(training.excluded) == 4
    assert all(r['path'].startswith('vivos_waves/') for r in training.excluded)
    assert Counter(i.extra['source'] for i in training.items)[DOMAIN_SOURCE] == 30
    files = {}
    with zipfile.ZipFile(data / 'ai_core.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((repo / 'ai-core/ai_core').rglob('*.py')):
            relative = path.relative_to(repo / 'ai-core').as_posix()
            files[relative] = sha(path)
            archive.write(path, relative)
    write(data / 'code_manifest.json', {'archive_sha256': sha(data / 'ai_core.zip'), 'files': files})
    write(data / 'dataset-metadata.json', {'title': 'ASR domain replay private supplement v1',
        'id': 'traininghighlight/asr-domain-replay-v1', 'isPrivate': True, 'licenses': [{'name': 'other'}]})
    kernel = Path(__file__).parent
    runner = kernel / 'run_asr_domain_replay.py'
    assert not runner.exists(), 'refusing to overwrite runner'
    shutil.copy2(repo / 'dist/kaggle/kernel-asr-robust/run_asr_robust.py', runner)
    write(kernel / 'kernel-metadata.json', {'id': 'traininghighlight/asr-domain-replay-guarded-v1',
        'title': 'ASR domain replay guarded v1', 'code_file': runner.name, 'language': 'python',
        'kernel_type': 'script', 'is_private': True, 'enable_gpu': True, 'enable_internet': False,
        'dataset_sources': ['traininghighlight/asr-domain-replay-v1', 'traininghighlight/asr-three-source-v1',
                            'traininghighlight/asr-robust-human', 'traininghighlight/vivos-asr'],
        'competition_sources': [], 'kernel_sources': []})
    assert all(sha(p) == h for p, h in guard.items())
    statistics = {source + '_' + split: {'examples': len(rows),
        'hours': sum(r['extra']['num_samples'] for r in rows) / 16000 / 3600}
        for source in recipe['sampling_probabilities'] for split in ('train', 'val', 'test')
        for rows in [[r for r in payload['items'] if r['extra']['source'] == source and r['split'] == split]]}
    report = {'status': 'PACKED_NOT_UPLOADED_OR_TRAINED', 'packet': str(data), 'recipe': recipe,
        'statistics': statistics, 'ctc_retained_training': len(training), 'exclusions': training.excluded,
        'source_sampling_counts': dict(Counter(i.extra['source'] for i in training.items)),
        'packet_hashes': {p.name: sha(p) for p in data.iterdir() if p.is_file()},
        'runner_sha256': sha(runner), 'protected_hashes': guard,
        'old_references_splits_unchanged': True, 'training_started': False, 'checkpoint_deployed': False,
        'limitations': ['Domain labels are user-attested human-corrected external ASR; not independent audio audit.',
                       'Domain train15minutes/val5minutes; fixed10 is development data, no independent domain test.',
                       'Prepares one500-step candidate; no measured GPU runtime/VRAM or quality improvement.',
                       'Existing remote input dataset versions/private status not rechecked during preparation.']}
    write(base / 'preflight.json', report)
    write(repo / 'data/manifests/asr_domain_replay_preparation.json', report)
    print('PACKED', data, 'TRAIN', len(training), 'SOURCE_COUNTS', report['source_sampling_counts'])


if __name__ == '__main__':
    main()
