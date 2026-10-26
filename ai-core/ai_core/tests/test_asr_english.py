import io
import tarfile

import numpy as np
import pytest
import soundfile as sf

from ai_core.scripts.prepare_asr_english import checked_member, check_splits, read_archive


@pytest.mark.parametrize('name,kind', [('../outside', tarfile.REGTYPE),
    ('/LibriSpeech/a', tarfile.REGTYPE), ('LibriSpeech/../../a', tarfile.REGTYPE),
    ('LibriSpeech/C:/a', tarfile.REGTYPE), ('LibriSpeech\\a', tarfile.REGTYPE),
    ('LibriSpeech/link', tarfile.SYMTYPE), ('LibriSpeech/link', tarfile.LNKTYPE)])
def test_unsafe_archive_member_rejected(name, kind):
    member = tarfile.TarInfo(name)
    member.type = kind
    with pytest.raises(ValueError):
        checked_member(member)


def test_pairing_decode_raw_label_and_no_overwrite(tmp_path):
    encoded = io.BytesIO()
    sf.write(encoded, np.linspace(-.2, .2, 32000), 16000, format='FLAC')
    archive = tmp_path / 'source.tar.gz'
    with tarfile.open(archive, 'w:gz') as output:
        for name, data in [('1-2.trans.txt', b'1-2-0001 We saw FTA 2020.\n'),
                           ('1-2-0001.flac', encoded.getvalue())]:
            member = tarfile.TarInfo('LibriSpeech/train-clean-5/1/2/' + name)
            member.size = len(data)
            output.addfile(member, io.BytesIO(data))
    row, = read_archive(archive, 'train-clean-5', 'train', tmp_path / 'out')
    assert row['extra']['raw_transcription'] == 'We saw FTA 2020.'
    assert row['extra']['transcript'] == 'WE SAW FTA 2020.'
    assert row['extra']['num_samples'] == 32000
    assert row['group'] == 'librispeech:1'
    assert read_archive(archive, 'train-clean-5', 'train', tmp_path / 'out') == [row]
    from pathlib import Path
    Path(row['path']).write_bytes(b'changed')
    with pytest.raises(AssertionError, match='existing audio differs'):
        read_archive(archive, 'train-clean-5', 'train', tmp_path / 'out')


def test_unpaired_transcript_rejected(tmp_path):
    archive = tmp_path / 'source.tar.gz'
    with tarfile.open(archive, 'w:gz') as output:
        data = b'1-2-0001 MISSING AUDIO\n'
        member = tarfile.TarInfo('LibriSpeech/train-clean-5/1/2/1-2.trans.txt')
        member.size = len(data)
        output.addfile(member, io.BytesIO(data))
    with pytest.raises(AssertionError, match='unpaired'):
        read_archive(archive, 'train-clean-5', 'train', tmp_path / 'out')


@pytest.mark.parametrize('key', ['group', 'audio_sha256', 'utterance_id', 'chapter_id'])
@pytest.mark.parametrize('pair', [(0, 1), (0, 2), (1, 2)])
def test_each_leakage_key_rejected(key, pair):
    rows = [{'split': split, 'group': str(i), 'extra': {
        'audio_sha256': str(i), 'utterance_id': str(i), 'chapter_id': str(i)}}
        for i, split in enumerate(['train', 'val', 'test'])]
    check_splits(rows)
    a, b = pair
    if key == 'group':
        rows[b][key] = rows[a][key]
    else:
        rows[b]['extra'][key] = rows[a]['extra'][key]
    with pytest.raises(AssertionError, match=key):
        check_splits(rows)
