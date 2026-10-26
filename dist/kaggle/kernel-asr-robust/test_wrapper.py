import importlib.util
import copy
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('asr_wrapper', Path(__file__).with_name('run_asr_robust.py'))
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


def test_kaggle_nested_archive_root(tmp_path):
    leaf = tmp_path / 'fleurs_audio/fleurs_audio'
    (leaf / 'train').mkdir(parents=True)
    (leaf / 'train/00000.flac').write_bytes(b'audio')
    assert wrapper.audio_root(tmp_path, 'fleurs_audio', 'fleurs_audio/train/00000.flac') == leaf
    with pytest.raises(AssertionError):
        wrapper.audio_root(tmp_path, 'fleurs_audio', 'fleurs_audio/train/missing.flac')


def test_archive_rejects_escaping_member(tmp_path):
    archive = tmp_path / 'audio.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('../outside', 'bad')
    with pytest.raises(AssertionError):
        wrapper.extract(archive, tmp_path / 'staging')
    assert not (tmp_path / 'outside').exists()


@pytest.mark.parametrize('auto_extracted', [False, True])
@pytest.mark.parametrize('domain_replay', [False, True])
def test_three_source_staging_binds_audio_and_preserves_labels(tmp_path, auto_extracted, domain_replay):
    root = tmp_path / 'input'
    legacy, vivos, data = [root / name for name in ('old', 'vivos', 'new')]
    for folder in (legacy, vivos, data):
        folder.mkdir(parents=True)
    (vivos / 'vivos.json').write_text('{}', encoding='utf-8')
    (legacy / 'asr_robust_manifest.json').write_text('{}', encoding='utf-8')
    english = root / 'english' if domain_replay else data
    english.mkdir(exist_ok=True)
    if domain_replay:
        (english / 'asr_three_source_manifest.json').write_text('{}', encoding='utf-8')
    payload = {'meta': {'vivos_manifest_sha256': wrapper.sha(vivos / 'vivos.json')}, 'items': []}
    archives = [(vivos, 'vivos_waves', 'vivos', 'vivos_archive_sha256'),
            (legacy, 'fleurs_audio', 'fleurs', 'fleurs_archive_sha256'),
            (english, 'english_audio', 'minilibrispeech', 'english_archive_sha256')]
    if domain_replay:
        archives.append((data, 'domain_audio', 'real_domain_user_review', 'domain_archive_sha256'))
    for parent, folder, domain, key in archives:
        relative = folder + '/train/a.flac'
        blob = domain.encode()
        with zipfile.ZipFile(parent / (folder + '.zip'), 'w') as archive:
            archive.writestr(relative, blob)
        payload['meta'][key] = wrapper.sha(parent / (folder + '.zip'))
        if auto_extracted:
            leaf = parent / folder / relative
            leaf.parent.mkdir(parents=True)
            leaf.write_bytes(blob)
            (parent / (folder + '.zip')).unlink()
        payload['items'].append({'path': relative, 'label': 'en' if domain == 'minilibrispeech' else 'vi',
            'split': 'train', 'group': domain, 'extra': {'source': domain, 'transcript': 'HÀ NỘI FTA 2020',
                'audio_sha256': hashlib.sha256(blob).hexdigest()}})
    before = copy.deepcopy(payload)
    staging = tmp_path / 'staged'
    staging.mkdir()
    path = wrapper.stage_audio(root, data, payload, staging)
    staged = json.loads(path.read_text(encoding='utf-8'))
    for old, new in zip(before['items'], staged['items']):
        absolute = new.pop('path')
        assert Path(absolute).is_file() and Path(absolute).is_relative_to(staging)
        assert new == {k: v for k, v in old.items() if k != 'path'}
    before['items'][-1]['extra']['audio_sha256'] = 'wrong hash'
    corrupt_stage = tmp_path / 'corrupt'
    corrupt_stage.mkdir()
    with pytest.raises(AssertionError):
        wrapper.stage_audio(root, data, before, corrupt_stage)
