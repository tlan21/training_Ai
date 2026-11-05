"""AI-25: pack football replay v1 = domain-replay v2 recipe/guard/val + 14 football clips typed from audio (user export
2026-11-05), started from the ACTIVE ASR 8f879867 (parent133 d03ef0a9 is worse on football: CER 99% vs 84%).

One bounded experiment; never trains or deploys. The 30 football eval clips stay OUT of the packet (final test, scored once
locally against the active ASR); selection uses the frozen 10-clip news domain val + VIVOS/FLEURS/MLS guards vs the active ASR.
"""
import copy
import hashlib
import json
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

from pack import write


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    repo = Path(__file__).resolve().parents[3]
    sys.path[:0] = [str(repo / 'ai-core'), str(repo / 'dist/kaggle/kernel-minigpt-domain'), str(Path(__file__).parent)]
    from ai_core.scripts.prepare_asr_robust import extend_chars
    from ai_core.scripts.finetune_asr_robust import data_identity, validate_recipe, RobustASRDataset, DOMAIN_SOURCE
    from ai_core.training.datasets import CharVocab
    from ai_core.training.checkpoint import load_checkpoint
    from asr_gold import validate as validate_verbatim
    from expansion_intake import validate as validate_expansion
    from football_intake import validate as validate_football
    import soundfile as sf

    old = Path('D:/data_training_ai/asr_three_source_v1_20261020/kaggle_dataset')
    domain = Path('D:/data_training_ai/minigpt_domain_v1_20261019/asr_verbatim_v1')
    expansion = Path('D:/data_training_ai/asr_domain_expansion_v2_20261022')
    football = Path('D:/data_training_ai/football_asr_sources')
    base = Path('D:/data_training_ai/asr_football_replay_v1_20261105')
    data = base / 'kaggle_dataset'
    assert not base.exists(), 'refusing to overwrite experiment'

    # v1 domain labels + fixed validation, exactly as in the v1 pack.
    intake = json.loads((repo / 'data/manifests/asr_verbatim_intake.json').read_text(encoding='utf-8'))
    source_labels = domain / ('received_' + intake['source_labels_sha256'][:12]) / 'asr_verbatim_domain_v1.json'
    assert sha(source_labels) == intake['source_labels_sha256']
    approved, pending = validate_verbatim(json.loads(source_labels.read_text(encoding='utf-8-sig')),
                                          json.loads((domain / 'packet.json').read_text(encoding='utf-8')))
    assert pending == {'train': [], 'val': []}
    frozen = domain / 'frozen_validation.json'
    references = [{'sample_id': r['sample_id'], 'audio_sha256': r['extra']['audio_sha256'], 'transcript': r['extra']['transcript']}
                  for r in sorted(approved['val'], key=lambda r: r['sample_id'])]
    assert references == json.loads(frozen.read_text(encoding='utf-8'))
    reference_identity = hashlib.sha256(json.dumps(references, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    # New: reviewed expansion export (train only).
    review = expansion / 'received_86f0ce11d0d9/asr_expansion_review_v2.json'
    assert sha(review).startswith('86f0ce11d0d9')
    extra, waiting = validate_expansion(json.loads(review.read_text(encoding='utf-8-sig')),
                                        json.loads((expansion / 'asr_review_v2/packet.json').read_text(encoding='utf-8')), expansion)
    assert len(extra) == 51 and len(waiting) == 9
    export = football / 'received_v1/asr_football_review_v1_20261105.json'
    assert sha(export).startswith('67b549878c46')
    kicks, _ = validate_football(json.loads(export.read_text(encoding='utf-8-sig')),
                                 json.loads((football / 'review_v1/packet.json').read_text(encoding='utf-8')), football / 'review_v1')
    kicks = [k for k in kicks if k['split'] == 'train']
    assert len(kicks) == 14
    for k in kicks:  # same item shape as the news domain rows; provenance HUMAN_VERIFIED / draft NONE kept
        k['extra'].update(source=DOMAIN_SOURCE, channel_id=k['extra']['channel'], video_sha256=None)
    train = approved['train'] + extra + kicks

    original = json.loads((old / 'asr_three_source_manifest.json').read_text(encoding='utf-8'))
    payload = copy.deepcopy(original)
    source = repo / 'ai-core/checkpoints/asr_ctc/best.pt'
    assert sha(source) == '8f87986781cfb3d4716691f2051e5798187693e2452f9f41b28ca4a753ea5531'
    payload['meta'].update(source_checkpoint_sha256=sha(source),
        previous_three_source_manifest_sha256=sha(old / 'asr_three_source_manifest.json'),
        domain_review_sha256=sha(source_labels), expansion_review_sha256=sha(review), football_review_sha256=sha(export),
        frozen_validation_sha256=sha(frozen),
        domain_validation_identity_sha256=reference_identity,
        domain_label_origin='human_reviewed_external_asr', domain_final_test_available=False)
    old_chars = json.loads((old / 'robust_vocab.json').read_text(encoding='utf-8'))['chars']
    chars = extend_chars(old_chars, [r['extra']['transcript'] for r in train])
    assert chars[:len(old_chars)] == old_chars
    saved = load_checkpoint(str(source))
    active = saved.get('char_vocab') or saved['metadata']['char_vocab']
    assert len(active) == 93 and (['<blank>'] + old_chars)[:93] == active, 'active symbols must be a prefix of parent133'
    data.mkdir(parents=True)
    with zipfile.ZipFile(data / 'domain_audio.zip', 'x', compression=zipfile.ZIP_STORED) as archive:
        for split, rows in (('train', train), ('val', approved['val'])):
            for row in rows:
                audio = Path(row['path'])
                assert sha(audio) == row['extra']['audio_sha256']
                info = sf.info(str(audio))
                assert info.samplerate == 16000 and info.channels == 1 and info.frames in (320000, 480000)
                item = {k: copy.deepcopy(v) for k, v in row.items() if k != 'sample_id'}
                item['path'] = 'domain_audio/' + audio.name
                item['extra']['num_samples'] = info.frames
                assert item['extra']['source'] == DOMAIN_SOURCE and item['split'] == split
                archive.write(audio, item['path'])
                payload['items'].append(item)
    assert payload['items'][:len(original['items'])] == original['items']
    payload['meta']['domain_archive_sha256'] = sha(data / 'domain_audio.zip')
    write(data / 'asr_domain_manifest.json', payload)
    write(data / 'robust_vocab.json', {'chars': chars})
    shutil.copy2(source, data / 'source_asr.pt')
    shutil.copy2(frozen, data / 'frozen_validation.json')
    recipe = {'id': 'asr-football-replay-v1', 'seed': 1337, 'steps': 500, 'eval_every': 100,
        'sampling_probabilities': {'vivos': .4, 'fleurs': .3, 'minilibrispeech': .2, DOMAIN_SOURCE: .1},
        'initial_checkpoint_sha256': sha(source), 'vocab_sha256': sha(data / 'robust_vocab.json'),
        'manifest_sha256': sha(data / 'asr_domain_manifest.json'), 'data_identity_sha256': data_identity(payload),
        'frozen_validation_sha256': sha(frozen), 'domain_validation_identity_sha256': reference_identity,
        'selection': 'all-domain-wer-cer-nonregression-and-domain-wer-cer-improvement'}
    validate_recipe(recipe, payload, sha(data / 'robust_vocab.json'), sha(source), 500)
    write(data / 'recipe.json', recipe)
    vocab = CharVocab(chars)
    training = RobustASRDataset(str(data / 'asr_domain_manifest.json'), 'train', vocab, augment=True)
    counts = Counter(i.extra['source'] for i in training.items)
    assert counts[DOMAIN_SOURCE] == 95, counts
    files = {}
    with zipfile.ZipFile(data / 'ai_core.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((repo / 'ai-core/ai_core').rglob('*.py')):
            relative = path.relative_to(repo / 'ai-core').as_posix()
            files[relative] = sha(path)
            archive.write(path, relative)
    write(data / 'code_manifest.json', {'archive_sha256': sha(data / 'ai_core.zip'), 'files': files})
    write(data / 'dataset-metadata.json', {'title': 'ASR football replay private supplement v1',
        'id': 'traininghighlight/asr-football-replay-v1', 'isPrivate': True, 'licenses': [{'name': 'other'}]})
    kernel = repo / 'dist/kaggle/kernel-asr-football-replay-v1'
    kernel.mkdir(exist_ok=False)
    shutil.copy2(Path(__file__).parent / 'run_asr_domain_replay.py', kernel / 'run_asr_domain_replay.py')
    write(kernel / 'kernel-metadata.json', {'id': 'traininghighlight/asr-football-replay-guarded-v1',
        'title': 'ASR football replay guarded v1', 'code_file': 'run_asr_domain_replay.py', 'language': 'python',
        'kernel_type': 'script', 'is_private': True, 'enable_gpu': True, 'enable_internet': False,
        'dataset_sources': ['traininghighlight/asr-football-replay-v1', 'traininghighlight/asr-three-source-v1',
                            'traininghighlight/asr-robust-human', 'traininghighlight/vivos-asr'],
        'competition_sources': [], 'kernel_sources': []})
    report = {'status': 'PACKED_NOT_UPLOADED_OR_TRAINED', 'packet': str(data), 'recipe': recipe,
        'domain_train_clips': {'v1_verbatim': len(approved['train']), 'expansion_reviewed': len(extra), 'football_typed': len(kicks)},
        'domain_val_clips': len(approved['val']), 'expansion_pending': waiting,
        'new_chars': chars[len(old_chars):], 'vocab_size_with_blank': len(chars) + 1,
        'ctc_retained_training': len(training), 'exclusions': training.excluded, 'source_sampling_counts': dict(counts),
        'packet_hashes': {p.name: sha(p) for p in data.iterdir() if p.is_file()},
        'training_started': False, 'checkpoint_deployed': False,
        'limitations': ['Only 14 football train clips (4.7 min); football share of samples ~1.5%: little change expected.',
                        'Selection domain val = 10 news clips; football 30-clip test kept outside and scored once against the active ASR.']}
    write(base / 'preflight.json', report)
    write(repo / 'data/manifests/asr_football_replay_v1_preparation.json', report)
    print('PACKED', data, 'TRAIN', len(training), 'SOURCES', dict(counts), 'NEW_CHARS', chars[len(old_chars):])


if __name__ == '__main__':
    main()
