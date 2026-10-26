"""Prepare human-read SLR31 English data; never changes the old ASR datasets or weights."""

import hashlib
import io
import json
import re
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath

from ai_core.data.manifest import split_by_group
from ai_core.scripts.prepare_asr_robust import extend_chars, normalize, sha
from ai_core.scripts.finetune_asr_robust import ctc_steps
from ai_core.training.datasets import CharVocab


SOURCES = {
    'train-clean-5': ('train', '5df7d4e78065366204ca6845bb08f490'),
    'dev-clean-2': ('val', '6d7ab67ac6a1d2c993d050e16d61080d'),
}


def checked_member(member):
    path = PurePosixPath(member.name)
    if (path.is_absolute() or '..' in path.parts or '\\' in member.name or ':' in member.name
            or not path.parts or path.parts[0] != 'LibriSpeech'
            or not (member.isfile() or member.isdir())):
        raise ValueError(f'Unsafe archive member: {member.name}')
    return path


def check_splits(rows):
    for key in ('group', 'audio_sha256', 'utterance_id', 'chapter_id'):
        def values(split):
            return {r[key] if key == 'group' else r['extra'][key] for r in rows if r['split'] == split}
        for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]:
            assert values(a) and values(b), 'empty split'
            assert not values(a) & values(b), f'{key} overlaps {a}/{b}'


def read_archive(path, official, split, output):
    import numpy as np
    import soundfile as sf

    rows, transcripts, audio_ids = [], {}, set()
    with tarfile.open(path, 'r:gz') as archive:
        members = archive.getmembers()
        for member in members:
            checked_member(member)
        for member in members:
            if member.name.endswith('.trans.txt'):
                for line in archive.extractfile(member).read().decode('utf-8').splitlines():
                    uid, raw = line.split(' ', 1)
                    assert re.fullmatch(r'\d+-\d+-\d+', uid) and uid not in transcripts
                    assert member.name == f'LibriSpeech/{official}/{uid.split("-")[0]}/{uid.split("-")[1]}/{"-".join(uid.split("-")[:2])}.trans.txt'
                    transcripts[uid] = raw
        for member in members:
            if not member.name.endswith('.flac'):
                continue
            relative = checked_member(member)
            uid = relative.stem
            assert uid in transcripts and uid not in audio_ids
            speaker, chapter, _ = uid.split('-')
            assert str(relative) == f'LibriSpeech/{official}/{speaker}/{chapter}/{uid}.flac'
            encoded = archive.extractfile(member).read()
            signal, rate = sf.read(io.BytesIO(encoded), dtype='float32')
            assert rate == 16000 and signal.ndim == 1 and len(signal) >= 400
            assert np.isfinite(signal).all() and np.any(signal != 0)
            text = normalize(transcripts[uid])
            destination = output / 'audio' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(encoded).hexdigest()
            if destination.exists():
                assert sha(destination) == digest, 'existing audio differs'
            else:
                with destination.open('xb') as stream:
                    stream.write(encoded)
            required = len(text) + sum(a == b for a, b in zip(text, text[1:]))
            rows.append({'path': str(destination.resolve()), 'label': 'en', 'split': split,
                         'group': 'librispeech:' + speaker,
                         'extra': {'source': 'minilibrispeech', 'transcript': text,
                                   'raw_transcription': transcripts[uid], 'utterance_id': uid,
                                   'chapter_id': chapter, 'official_split': official,
                                   'audio_sha256': digest, 'num_samples': len(signal),
                                   'ctc_feasible': ctc_steps(len(signal)) >= required}})
            audio_ids.add(uid)
    assert transcripts and set(transcripts) == audio_ids, 'unpaired transcript/audio'
    return rows


def main():
    base = Path('D:/data_training_ai/asr_english_v1_20261020')
    repo = Path(__file__).resolve().parents[3]
    output = base / 'prepared'
    assert not (output / 'english_manifest.json').exists(), 'refusing to replace prepared data'
    previous = Path('D:/data_training_ai/asr_robust/kaggle_dataset')
    candidate = Path('D:/data_training_ai/asr_robust/outputs-v2/asr_robust_run/asr_ctc/best.pt')
    review = Path('D:/data_training_ai/minigpt_domain_v1_20261019/whisper_review_v1/received_860f8068d0bd/reviewed_whisper_domain_v1.json')
    guard = json.loads(Path('D:/data_training_ai/minigpt_domain_v1_20261019/frozen_guard.json').read_text(encoding='utf-8'))
    for path in [previous / 'asr_robust_manifest.json', previous / 'robust_vocab.json', candidate, review]:
        guard[str(path)] = sha(path)
    assert guard[str(candidate)] == 'd03ef0a962220618e90e5ff478a2fbab5ff35dd68deb539a4933eb7c15a4f3de'
    assert guard[str(review)] == '860f8068d0bd16398bbf1d2fd99bc24e276e01c55ca6b5343c78df757ca9e5a4'
    assert all(sha(path) == digest for path, digest in guard.items()), 'protected input changed'
    sources, rows = {}, []
    for official, (split, expected) in SOURCES.items():
        archive = base / 'raw' / (official + '.tar.gz')
        with archive.open('rb') as stream:
            assert hashlib.file_digest(stream, 'md5').hexdigest() == expected, 'upstream MD5 mismatch'
        sources[official] = {'url': f'https://openslr.elda.org/resources/31/{archive.name}',
                             'published_md5': expected, 'sha256': sha(archive), 'bytes': archive.stat().st_size}
        rows.extend(read_archive(archive, official, split, output))
        print(official, len(rows), 'cumulative audio/label pairs validated', flush=True)
    # Freeze the new English held-out partition by speaker, before model evaluation.
    heldout = [r for r in rows if r['extra']['official_split'] == 'dev-clean-2']
    partition = split_by_group([r['group'] for r in heldout], ratios=(0, .5, .5), seed=1337)
    for row in heldout:
        row['split'] = partition[row['group']]
    check_splits(rows)
    old_chars = json.loads((previous / 'robust_vocab.json').read_text(encoding='utf-8'))['chars']
    from ai_core.training.checkpoint import load_checkpoint
    saved = load_checkpoint(str(candidate))
    assert ['<blank>'] + old_chars == (saved.get('char_vocab') or saved['metadata']['char_vocab'])
    chars = extend_chars(old_chars, [r['extra']['transcript'] for r in rows if r['split'] == 'train'])
    vocab = CharVocab(chars)
    for row in rows:
        if row['split'] == 'train':
            text = row['extra']['transcript']
            assert vocab.decode(vocab.encode(text)) == text
    statistics = {}
    for split in ('train', 'val', 'test'):
        selected = [r for r in rows if r['split'] == split]
        statistics[split] = {'examples': len(selected),
                             'hours': sum(r['extra']['num_samples'] for r in selected) / 16000 / 3600,
                             'speakers': len({r['group'] for r in selected}),
                             'ctc_infeasible': sum(not r['extra']['ctc_feasible'] for r in selected),
                             'oov_characters': sorted(set(''.join(r['extra']['transcript'] for r in selected)) - set(chars))}
    old_rows = json.loads((previous / 'asr_robust_manifest.json').read_text(encoding='utf-8'))['items']
    # shortcut: keyword matches only identify old replay candidates; require human/audio review for domain gold.
    terms = {'english_acronym': r'\b(?:FTA|WTO|CPTPP|IELTS|OCOP|RT-PCR)\b',
             'numeric_written_form': r'\d', 'legal_words': r'\b(?:NGHỊ QUYẾT|THÔNG TƯ|ĐIỀU KHOẢN|NGHỊ ĐỊNH)\b',
             'place_keywords': r'\b(?:LÀO CAI|HÀ NỘI|HẢI PHÒNG)\b',
             'compound_keywords': r'\b(?:CHỦ TRÌ|THIẾT YẾU|LĨNH VỰC)\b'}
    replay = []
    for row in old_rows:
        if row['split'] != 'train':
            continue
        tags = [tag for tag, pattern in terms.items() if re.search(pattern, row['extra']['transcript'])]
        if tags:
            replay.append({'path': row['path'], 'group': row['group'], 'source': row['extra']['source'],
                           'transcript': row['extra']['transcript'], 'tags': tags})
    report = {'status': 'PREPARED_HUMAN_ENGLISH_DATA_NOT_TRAINED', 'source_page': 'https://www.openslr.org/31/',
              'license': 'CC-BY-4.0', 'provenance': 'LibriVox human-read audiobooks, upstream segmented/aligned book text; no ASR-generated labels',
              'normalization': 'asr-label-v1-lossless: NFC uppercase whitespace collapse; preserve raw text',
              'sources': sources, 'statistics': statistics, 'candidate_checkpoint_sha256': sha(candidate),
              'heldout_partition': {'seed': 1337, 'rule': 'dev-clean-2 speakers shuffled once, floor(n/2) val, remainder test',
                                    'speaker_mapping': partition},
              'vocab_size': vocab.size, 'old_ids_preserved': chars[:len(old_chars)] == old_chars,
              'train_only_added_characters': chars[len(old_chars):],
              'exact_normalized_text_overlap': {a + '_' + b: len(
                  {r['extra']['transcript'] for r in rows if r['split'] == a} &
                  {r['extra']['transcript'] for r in rows if r['split'] == b})
                  for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]},
              'old_vietnamese_replay': {'examples': len(replay), 'tag_counts': dict(Counter(t for r in replay for t in r['tags'])),
                                        'new_data': False, 'keyword_matches_are_not_domain_verification': True},
              'protected_hashes': guard,
              'limitations': ['Read English is not Vietnamese-English code switching or legal/news audio.',
                              'No new Vietnamese numeric/legal/name gold labels; 40 Whisper reviews stay unapproved.',
                              'Speaker/chapter/audio-hash separation checked inside SLR31 only; semantic near-duplicates not certified.',
                              'English val/test are speaker partitions of upstream dev-clean-2; original Vietnamese tests remain frozen.',
                              'Existing two-source robust trainer needs a separate three-source recipe/staging task before training.'],
              'training_started': False, 'promoted': False}
    assert all(sha(path) == digest for path, digest in guard.items()), 'protected file changed'
    for name, payload in [('english_manifest.json', {'meta': report, 'items': rows}),
                           ('english_vocab.json', {'chars': chars}), ('old_vi_replay_candidates.json', replay)]:
        with (output / name).open('x', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
    report['prepared_files'] = {name: sha(output / name) for name in
                                ['english_manifest.json', 'english_vocab.json', 'old_vi_replay_candidates.json']}
    for path in [base / 'preflight.json', repo / 'data/manifests/asr_english_preparation.json']:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in ['status', 'statistics', 'vocab_size', 'old_vietnamese_replay']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
