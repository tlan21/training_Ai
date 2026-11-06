"""AI-29: pack the union dataset for the from-scratch ASR trial = public expansion manifest (VIVOS/FLEURS/MLS/FOSD/CV + 95/10 domain)
+ the 294 channel-verified creator clips of football replay v2. Audio: public_audio.pack stays in Kaggle dataset asr-public-expand-v1;
domain_audio (v2, incl. creator) ships here renamed .pack (no auto-extract). Never trains.
"""
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
    sys.path[:0] = [str(repo / 'ai-core'), str(Path(__file__).parent)]
    from ai_core.scripts.prepare_asr_robust import extend_chars

    public = Path('D:/data_training_ai/asr_public_expand_v1_20261105/kaggle_dataset')
    football2 = Path('D:/data_training_ai/asr_football_replay_v2_20261106/kaggle_dataset')
    data = Path('D:/data_training_ai/asr_scratch_v1_20261106/kaggle_dataset')
    assert not data.parent.exists(), 'refusing to overwrite experiment'
    pub = json.loads((public / 'asr_domain_manifest.json').read_text(encoding='utf-8'))
    f2 = json.loads((football2 / 'asr_domain_manifest.json').read_text(encoding='utf-8'))
    creator = [i for i in f2['items'] if i['extra'].get('label_origin') == 'CREATOR_SUBTITLE_CHANNEL_VERIFIED']
    assert len(creator) == 294
    payload = {'meta': {**pub['meta'], 'source_checkpoint_sha256': None, 'task': 'AI-29 scratch ASR union',
                        'domain_archive_sha256': f2['meta']['domain_archive_sha256'],
                        'creator_review_sha256_prefix': f2['meta']['creator_review_sha256_prefix'],
                        'public_manifest_sha256': sha(public / 'asr_domain_manifest.json'),
                        'football2_manifest_sha256': sha(football2 / 'asr_domain_manifest.json')},
               'items': pub['items'] + creator}
    paths = [i['path'] for i in payload['items']]
    assert len(paths) == len(set(paths)), 'duplicate audio path'
    old = json.loads((public / 'robust_vocab.json').read_text(encoding='utf-8'))['chars']
    chars = extend_chars(old, [i['extra']['transcript'] for i in creator])
    data.mkdir(parents=True)
    write(data / 'scratch_manifest.json', payload)
    write(data / 'robust_vocab.json', {'chars': chars})
    shutil.copy2(football2 / 'domain_audio.zip', data / 'domain_audio.pack')
    assert sha(data / 'domain_audio.pack') == payload['meta']['domain_archive_sha256']
    shutil.copy2(Path(__file__).parent / 'run_asr_domain_replay.py', data / 'asr_stage.py')
    with zipfile.ZipFile(data / 'ai_core.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((repo / 'ai-core/ai_core').rglob('*.py')):
            archive.write(path, path.relative_to(repo / 'ai-core').as_posix())
        for path in sorted((repo / 'ai-core/ai_core/training/configs').glob('*.yaml')):
            archive.write(path, path.relative_to(repo / 'ai-core').as_posix())
    write(data / 'dataset-metadata.json', {'title': 'ASR scratch union private supplement v1',
        'id': 'traininghighlight/asr-scratch-v1', 'isPrivate': True, 'licenses': [{'name': 'other'}]})
    counts = Counter((i['extra']['source'], i['split']) for i in payload['items'])
    report = {'status': 'PACKED_NOT_UPLOADED_OR_TRAINED', 'items': len(payload['items']), 'counts': {f'{a}/{b}': n for (a, b), n in sorted(counts.items())},
              'vocab_size_with_blank': len(chars) + 1, 'new_chars': chars[len(old):], 'manifest_sha256': sha(data / 'scratch_manifest.json')}
    write(data.parent / 'preflight.json', report)
    write(repo / 'data/manifests/asr_scratch_v1_preparation.json', report)
    print('PACKED', json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
