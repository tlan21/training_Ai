"""AI-31: pack football replay v3 = football replay v1 packet (VIVOS/FLEURS/MLS + 95/10 domain incl. 14 football) + 14 more
football clips typed from audio (review_v1 round 2 + review_v2 train channels) = 28 football train clips. No creator rows.
Initial = ACTIVE ASR 7c497d43. Never trains or deploys.
"""
import hashlib
import json
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

from pack import write

ACTIVE = '7c497d43ce9ca9fbb4d29f80e2d86e777d11f7eea6828062e581fce4aa794934'
SOURCES = Path('D:/data_training_ai/football_asr_sources')
EXPORTS = (('received_v1_r2/asr_football_review_v1_r2.json', 'review_v1', '5ab3daf2'),
           ('received_v2/asr_football_review_v2.json', 'review_v2', 'e61abe25'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    repo = Path(__file__).resolve().parents[3]
    sys.path[:0] = [str(repo / 'ai-core'), str(Path(__file__).parent)]
    from ai_core.scripts.prepare_asr_robust import extend_chars
    from ai_core.scripts.finetune_asr_robust import (data_identity, validate_recipe, RobustASRDataset, DOMAIN_SOURCE,
                                                     FOOTBALL3_RECIPE, FOOTBALL2_PROBABILITIES)
    from ai_core.training.datasets import CharVocab
    from football_intake import validate as validate_football
    import soundfile as sf

    prev = Path('D:/data_training_ai/asr_football_replay_v1_20261105/kaggle_dataset')
    base = Path('D:/data_training_ai/asr_football_replay_v3_20261111')
    data = base / 'kaggle_dataset'
    assert not base.exists(), 'refusing to overwrite experiment'
    prev_recipe = json.loads((prev / 'recipe.json').read_text(encoding='utf-8'))
    assert sha(prev / 'asr_domain_manifest.json') == prev_recipe['manifest_sha256']
    payload = json.loads((prev / 'asr_domain_manifest.json').read_text(encoding='utf-8'))
    original = len(payload['items'])
    assert sha(repo / 'ai-core/checkpoints/asr_ctc/best.pt') == ACTIVE
    old_chars = json.loads((prev / 'robust_vocab.json').read_text(encoding='utf-8'))['chars']
    have = {i['extra']['audio_sha256'] for i in payload['items']}
    test_videos, kicks = set(), []
    for export, review, prefix in EXPORTS:
        assert sha(SOURCES / export).startswith(prefix)
        packet = json.loads((SOURCES / review / 'packet.json').read_text(encoding='utf-8'))
        test_videos |= {s['video_id'] for s in packet['samples'] if s['split'] == 'val'}
        approved, _ = validate_football(json.loads((SOURCES / export).read_text(encoding='utf-8-sig')), packet, SOURCES / review)
        kicks += [k for k in approved if k['split'] == 'train' and k['extra']['audio_sha256'] not in have]
    assert len(kicks) == 14, len(kicks)
    assert not {k['extra']['video_id'] for k in kicks} & test_videos, 'football test video leaked into train'
    data.mkdir(parents=True)
    with zipfile.ZipFile(prev / 'domain_audio.zip') as old, zipfile.ZipFile(data / 'domain_audio.zip', 'x', compression=zipfile.ZIP_STORED) as new:
        for name in old.namelist():
            new.writestr(name, old.read(name))
        for k in kicks:  # same item shape as the v1 football rows; provenance HUMAN_VERIFIED / draft NONE kept
            audio = Path(k['path'])
            info = sf.info(str(audio))
            assert info.samplerate == 16000 and info.channels == 1 and sha(audio) == k['extra']['audio_sha256']
            item = {key: v for key, v in k.items() if key != 'sample_id'}
            item['path'] = 'domain_audio/' + audio.name
            item['extra'] = {**k['extra'], 'source': DOMAIN_SOURCE, 'channel_id': k['extra']['channel'], 'video_sha256': None,
                             'num_samples': info.frames}
            new.write(audio, item['path'])
            payload['items'].append(item)
    payload['meta'].update(source_checkpoint_sha256=ACTIVE, previous_football_replay_manifest_sha256=prev_recipe['manifest_sha256'],
                           domain_archive_sha256=sha(data / 'domain_audio.zip'),
                           football_review_v1_r2_sha256=sha(SOURCES / EXPORTS[0][0]), football_review_v2_sha256=sha(SOURCES / EXPORTS[1][0]))
    chars = extend_chars(old_chars, [i['extra']['transcript'] for i in payload['items'] if i['split'] == 'train'])
    assert chars == old_chars, chars[len(old_chars):]
    write(data / 'asr_domain_manifest.json', payload)
    write(data / 'robust_vocab.json', {'chars': chars})
    shutil.copy2(repo / 'ai-core/checkpoints/asr_ctc/best.pt', data / 'source_asr.pt')
    shutil.copy2(prev / 'frozen_validation.json', data / 'frozen_validation.json')
    recipe = {'id': FOOTBALL3_RECIPE, 'seed': 1337, 'steps': 1000, 'eval_every': 100, 'sampling_probabilities': FOOTBALL2_PROBABILITIES,
              'initial_checkpoint_sha256': ACTIVE, 'vocab_sha256': sha(data / 'robust_vocab.json'),
              'manifest_sha256': sha(data / 'asr_domain_manifest.json'), 'data_identity_sha256': data_identity(payload),
              'frozen_validation_sha256': prev_recipe['frozen_validation_sha256'],
              'domain_validation_identity_sha256': prev_recipe['domain_validation_identity_sha256'],
              'selection': 'all-domain-wer-cer-nonregression-and-domain-wer-cer-improvement'}
    validate_recipe(recipe, payload, sha(data / 'robust_vocab.json'), ACTIVE, 1000)
    write(data / 'recipe.json', recipe)
    training = RobustASRDataset(str(data / 'asr_domain_manifest.json'), 'train', CharVocab(chars), augment=True)
    counts = Counter(i.extra['source'] for i in training.items)
    files = {}
    with zipfile.ZipFile(data / 'ai_core.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((repo / 'ai-core/ai_core').rglob('*.py')):
            relative = path.relative_to(repo / 'ai-core').as_posix()
            files[relative] = sha(path)
            archive.write(path, relative)
    write(data / 'code_manifest.json', {'archive_sha256': sha(data / 'ai_core.zip'), 'files': files})
    write(data / 'dataset-metadata.json', {'title': 'ASR football replay private supplement v3',
        'id': 'traininghighlight/asr-football-replay-v3', 'isPrivate': True, 'licenses': [{'name': 'other'}]})
    kernel = repo / 'dist/kaggle/kernel-asr-football-replay-v3'
    kernel.mkdir(exist_ok=False)
    shutil.copy2(Path(__file__).parent / 'run_asr_domain_replay.py', kernel / 'run_asr_domain_replay.py')
    write(kernel / 'kernel-metadata.json', {'id': 'traininghighlight/asr-football-replay-guarded-v3',
        'title': 'ASR football replay guarded v3', 'code_file': 'run_asr_domain_replay.py', 'language': 'python',
        'kernel_type': 'script', 'is_private': True, 'enable_gpu': True, 'enable_internet': False,
        'dataset_sources': ['traininghighlight/asr-football-replay-v3', 'traininghighlight/asr-three-source-v1',
                            'traininghighlight/asr-robust-human', 'traininghighlight/vivos-asr'],
        'competition_sources': [], 'kernel_sources': []})
    preflight = {'status': 'PACKED_NOT_UPLOADED_OR_TRAINED', 'recipe': recipe, 'football_added': len(kicks), 'original_items': original,
                 'ctc_retained_training_by_source': dict(counts), 'excluded_total': len(training.excluded),
                 'training_started': False, 'checkpoint_deployed': False,
                 'limitations': ['28 football train clips (~9 min), ~5% of samples: small change expected.',
                                 'Selection domain val = 10 news clips; the 59-clip football test v2 is scored once outside the kernel.']}
    write(base / 'preflight.json', preflight)
    write(repo / 'data/manifests/asr_football_replay_v3_preparation.json', preflight)
    print('PACKED', json.dumps({k: preflight[k] for k in ('football_added', 'ctc_retained_training_by_source', 'excluded_total')}))


if __name__ == '__main__':
    main()
