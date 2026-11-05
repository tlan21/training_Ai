"""AI-27: pack public expansion = football replay v1 packet (VIVOS/FLEURS/MLS + 95/10 domain clips) + FOSD + Common Voice vi.

FOSD = FPT Open Speech Dataset (CC BY 4.0, human-prompted read speech, 2018; HF mirror doof-ferb/fpt_fosd checked line by line
against the Mendeley transcriptAll.txt). Common Voice 19.0 vi (CC0; mirror fsicoli/common_voice_19_0, official train/dev/test).
Initial = ACTIVE ASR 7c497d43 (136 symbols). One bounded experiment; never trains or deploys.
"""
import csv
import hashlib
import io
import json
import random
import re
import shutil
import sys
import tarfile
import zipfile
from collections import Counter
from pathlib import Path

from pack import write

ACTIVE = '7c497d43ce9ca9fbb4d29f80e2d86e777d11f7eea6828062e581fce4aa794934'
FOSD_LICENSE = 'CC BY 4.0 — FPT Open Speech Dataset (FPT Corporation 2018), Mendeley Data k9sxg2twv4 v4'
CV_LICENSE = 'CC0 1.0 — Mozilla Common Voice 19.0 vi'
FOSD_VAL = FOSD_TEST = CV_VAL_CAP = 300


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_fosd(text):
    """Original Mendeley transcript minus annotation markup: '-N' noise tags, literal backslash-r-backslash-n, spaces before punctuation."""
    text = text.replace(chr(92) + 'r' + chr(92) + 'n', ' ')  # the release contains these 4 literal characters
    text = ' '.join(w for w in text.split() if w != '-N')
    return re.sub(r'\s+([,.?!;:])', lambda m: m.group(1), text)


def words(text):
    return re.findall(r'\w+', text.casefold())


def main():
    repo = Path(__file__).resolve().parents[3]
    sys.path[:0] = [str(repo / 'ai-core'), str(Path(__file__).parent)]
    from ai_core.scripts.prepare_asr_robust import extend_chars, normalize
    from ai_core.scripts.finetune_asr_robust import data_identity, validate_recipe, RobustASRDataset, PUBLIC_PROBABILITIES, PUBLIC_RECIPE
    from ai_core.training.datasets import CharVocab
    from ai_core.training.checkpoint import load_checkpoint
    import pyarrow.parquet as pq
    import soundfile as sf

    prev = Path('D:/data_training_ai/asr_football_replay_v1_20261105/kaggle_dataset')
    pub = Path('D:/data_training_ai/asr_public_v1')
    base = Path('D:/data_training_ai/asr_public_expand_v1_20261105')
    data = base / 'kaggle_dataset'
    assert not base.exists(), 'refusing to overwrite experiment'
    prev_recipe = json.loads((prev / 'recipe.json').read_text(encoding='utf-8'))
    assert sha(prev / 'asr_domain_manifest.json') == prev_recipe['manifest_sha256']
    payload = json.loads((prev / 'asr_domain_manifest.json').read_text(encoding='utf-8'))
    original_items = len(payload['items'])
    source = repo / 'ai-core/checkpoints/asr_ctc/best.pt'
    assert sha(source) == ACTIVE
    saved = load_checkpoint(str(source))
    old_chars = json.loads((prev / 'robust_vocab.json').read_text(encoding='utf-8'))['chars']
    assert (saved.get('char_vocab') or saved['metadata']['char_vocab']) == ['<blank>'] + old_chars

    mendeley = {}
    for line in (pub / 'fosd/transcriptAll.txt').read_text(encoding='utf-8').splitlines():
        if line.count('|') >= 2:
            name, text = line.split('|')[:2]
            mendeley[name] = text
    parquets = sorted((pub / 'fosd').glob('train-*.parquet'))

    def fosd_rows():  # streamed: the 820 MB of mp3 bytes never sit in memory at once
        for f in parquets:
            for batch in pq.ParquetFile(f).iter_batches(batch_size=256):
                yield from batch.to_pylist()

    names = sorted(r['audio']['path'] for r in fosd_rows())
    assert len(names) == len(set(names))
    random.Random(1337).shuffle(names)
    split_of = {n: 'val' for n in names[:FOSD_VAL]} | {n: 'test' for n in names[FOSD_VAL:FOSD_VAL + FOSD_TEST]}
    report = Counter()
    seen, items = set(), []

    def add(archive, blob, path, text, split, group, src, licence, extra):
        digest = hashlib.sha256(blob).hexdigest()
        if digest in seen:
            report[f'{src}_duplicate_audio'] += 1
            return
        if not text.strip():
            report[f'{src}_empty_transcript'] += 1
            return
        signal, rate = sf.read(io.BytesIO(blob))
        seen.add(digest)
        archive.writestr(path, blob)
        items.append({'path': path, 'label': 'vi', 'split': split, 'group': group, 'extra': {
            'source': src, 'transcript': normalize(text), 'raw_transcription': text, 'audio_sha256': digest,
            'num_samples': round(len(signal) * 16000 / rate), 'license': licence, 'label_origin': 'HUMAN_PROMPTED_READ', **extra}})
        report[f'{src}_{split}'] += 1

    data.mkdir(parents=True)
    with zipfile.ZipFile(data / 'public_audio.zip', 'x', compression=zipfile.ZIP_STORED) as archive:
        for r in fosd_rows():
            name = r['audio']['path']
            text = clean_fosd(mendeley.get(name, ''))  # label = original FPT release; the mirror only supplies audio bytes
            if words(text) != words(r['transcription']):
                report['fosd_transcript_mismatch_vs_mendeley'] += 1
                continue
            add(archive, r['audio']['bytes'], f'public_audio/fosd/{name}', text, split_of.get(name, 'train'), 'fosd_' + name,
                'fosd', FOSD_LICENSE, {'set': name.split('_')[1]})
        for tsv, split in (('train', 'train'), ('dev', 'val'), ('test', 'test')):
            with tarfile.open(pub / f'cv19/vi_{tsv}.tar') as tar:
                members = {Path(m.name).name: m for m in tar.getmembers() if m.isfile()}
                clips = list(csv.DictReader((pub / f'cv19/{tsv}.tsv').open(encoding='utf-8'), delimiter='\t'))
                if split == 'val' and len(clips) > CV_VAL_CAP:
                    clips = random.Random(1337).sample(clips, CV_VAL_CAP)
                for c in clips:
                    member = members.get(c['path'])
                    if member is None:
                        report['commonvoice_missing_audio'] += 1
                        continue
                    add(archive, tar.extractfile(member).read(), f'public_audio/cv/{c["path"]}', c['sentence'], split,
                        'cv_' + c['client_id'], 'commonvoice', CV_LICENSE, {'up_votes': c['up_votes'], 'down_votes': c['down_votes']})
    # 1 known: mirror fixed a typo of the original ('gữi' -> 'gửi', Set001_011935); mismatching clips are excluded, not relabelled
    assert report['fosd_transcript_mismatch_vs_mendeley'] <= 5, report
    payload['items'] += items
    payload['meta'].update(source_checkpoint_sha256=ACTIVE, previous_football_replay_manifest_sha256=prev_recipe['manifest_sha256'],
                           public_archive_sha256=sha(data / 'public_audio.zip'),
                           public_sources={'fosd': FOSD_LICENSE, 'commonvoice': CV_LICENSE})
    chars = extend_chars(old_chars, [i['extra']['transcript'] for i in payload['items'] if i['split'] == 'train'])
    write(data / 'asr_domain_manifest.json', payload)
    write(data / 'robust_vocab.json', {'chars': chars})
    shutil.copy2(source, data / 'source_asr.pt')
    for name in ('frozen_validation.json', 'domain_audio.zip'):
        shutil.copy2(prev / name, data / name)
    recipe = {'id': PUBLIC_RECIPE, 'seed': 1337, 'steps': 3000, 'eval_every': 500, 'sampling_probabilities': PUBLIC_PROBABILITIES,
              'initial_checkpoint_sha256': ACTIVE, 'vocab_sha256': sha(data / 'robust_vocab.json'),
              'manifest_sha256': sha(data / 'asr_domain_manifest.json'), 'data_identity_sha256': data_identity(payload),
              'frozen_validation_sha256': prev_recipe['frozen_validation_sha256'],
              'domain_validation_identity_sha256': prev_recipe['domain_validation_identity_sha256'],
              'selection': 'all-domain-wer-cer-nonregression-and-domain-wer-cer-improvement'}
    validate_recipe(recipe, payload, sha(data / 'robust_vocab.json'), ACTIVE, 3000)
    write(data / 'recipe.json', recipe)
    training = RobustASRDataset(str(data / 'asr_domain_manifest.json'), 'train', CharVocab(chars), augment=True)
    files = {}
    with zipfile.ZipFile(data / 'ai_core.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((repo / 'ai-core/ai_core').rglob('*.py')):
            relative = path.relative_to(repo / 'ai-core').as_posix()
            files[relative] = sha(path)
            archive.write(path, relative)
    write(data / 'code_manifest.json', {'archive_sha256': sha(data / 'ai_core.zip'), 'files': files})
    write(data / 'dataset-metadata.json', {'title': 'ASR public expansion private supplement v1',
        'id': 'traininghighlight/asr-public-expand-v1', 'isPrivate': True, 'licenses': [{'name': 'other'}]})
    kernel = repo / 'dist/kaggle/kernel-asr-public-expand-v1'
    kernel.mkdir(exist_ok=False)
    shutil.copy2(Path(__file__).parent / 'run_asr_domain_replay.py', kernel / 'run_asr_domain_replay.py')
    write(kernel / 'kernel-metadata.json', {'id': 'traininghighlight/asr-public-expand-guarded-v1',
        'title': 'ASR public expansion guarded v1', 'code_file': 'run_asr_domain_replay.py', 'language': 'python',
        'kernel_type': 'script', 'is_private': True, 'enable_gpu': True, 'enable_internet': False,
        'dataset_sources': ['traininghighlight/asr-public-expand-v1', 'traininghighlight/asr-three-source-v1',
                            'traininghighlight/asr-robust-human', 'traininghighlight/vivos-asr'],
        'competition_sources': [], 'kernel_sources': []})
    counts = Counter(i.extra['source'] for i in training.items)
    preflight = {'status': 'PACKED_NOT_UPLOADED_OR_TRAINED', 'recipe': recipe, 'public_counts': dict(report),
                 'original_items': original_items, 'public_items': len(items), 'new_chars': chars[len(old_chars):],
                 'ctc_retained_training_by_source': dict(counts), 'exclusions': training.excluded[:50],
                 'excluded_total': len(training.excluded), 'training_started': False, 'checkpoint_deployed': False,
                 'limitations': ['FOSD has no speaker ids: val/test split by file, speakers may overlap across splits.',
                                 'Common Voice vi train has a single speaker (official split); dev/test are other speakers.',
                                 'Both are read speech; no football commentary in the public data.']}
    write(base / 'preflight.json', preflight)
    write(repo / 'data/manifests/asr_public_expand_v1_preparation.json', preflight)
    print('PACKED', json.dumps({k: preflight[k] for k in ('public_counts', 'ctc_retained_training_by_source', 'new_chars', 'excluded_total')},
                               ensure_ascii=False))


if __name__ == '__main__':
    main()
