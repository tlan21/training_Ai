"""Screen editorial pairs for the actual 512/96 serving profile; never generate labels."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from ..data.manifest import file_checksum
from ..tokenizer import BPETokenizer
from ..training.datasets.summary_dataset import CONTROL_TOKENS, normalize_to_asr, summary_prompt_ids
from .prepare_news_summary import record

PROTOCOL = 'sum-aligned-v1'
CONTEXT, OUTPUT_TOKENS, CER = 512, 96, 0.1347
VAL_COUNT = 64
PUBLISHER_PREFIX = re.compile(
    r'^\((?:Chinhphu\.vn|GDVN|TNO|HNMO|VOV|VTV|TBKTSG(?: Online)?|Dân trí)\)\s*[-–—:]?\s*', re.I)


def clean_label(text):
    return PUBLISHER_PREFIX.sub('', text.strip(), count=1)


def has_sentence_ending(text):
    """Reject terminal teaser ellipses; punctuation alone still cannot certify meaning."""
    suffix = r'["”’\')\]]*$'
    return bool(re.search(r'[.!?]'+suffix, text.rstrip())
                and not re.search(r'(?:\.{2,}|…)'+suffix, text.rstrip()))


def pair_sha(row):
    fields = {k: row[k] for k in ('id', 'body', 'source_asr', 'title', 'summary')}
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def screen_pair(row, tok):
    title, target = clean_label(row['title']), clean_label(row['summary'])
    body = row['body'].strip()
    if body.isupper():
        body = body.lower()  # Match production's CTC case handling.
    if len(target.split()) < 5:
        return None, 'short_summary'
    if not has_sentence_ending(target):
        return None, 'incomplete_summary'
    if any(len(tok.encode(t)) >= OUTPUT_TOKENS for t in (target, title)):
        return None, 'target_over_budget'
    # shortcut: lexical support cannot verify relations/negation; require a separate human audit before training.
    words = lambda s: set(re.findall(r'\w+', s.casefold()))
    numbers = lambda s: set(re.findall(r'\d+(?:[.,/:\-]\d+)*%?', s))
    if (numbers(target) | numbers(title)) - numbers(body):
        return None, 'unsupported_numeric_span'
    if (words(target) | words(title)) - words(body):
        return None, 'unsupported_target_word'
    seed = int(row['id'][:8], 16)
    asr = normalize_to_asr(body, cer=CER, seed=seed)
    for name, source in (('clean', body), ('asr', asr)):
        ids = tok.encode(' '+source)
        for fmt, marker in CONTROL_TOKENS.items():
            prompt = tok.encode(marker)+ids+[tok.special_tokens['<eos>']]
            if len(prompt) > CONTEXT-OUTPUT_TOKENS:
                return None, f'{name}_source_over_budget'
            assert prompt == summary_prompt_ids(source, tok, fmt, CONTEXT, OUTPUT_TOKENS)
        assert tok.decode(ids) == ' '+source
    return {'id': row['id'], 'title': title, 'summary': target, 'body': body,
            'source_asr': asr, 'noise_seed': seed}, None


def check_human_audit(path, manifest, parts):
    """A sampled annotation gate, not a claim that all candidate labels are verified."""
    expected = {(r['split'], r['id']): r['pair_sha256'] for r in manifest['audit_sample']}
    actual = {(split, row['id']): pair_sha(row) for split, rows in parts.items() for row in rows
              if (split, row['id']) in expected}
    if not expected or actual != expected:
        raise ValueError('human audit sample no longer matches prepared pairs')
    with path.open(encoding='utf-8-sig', newline='') as source:
        rows = list(csv.DictReader(source))
    if len(rows) != len(expected) or len({(r['split'], r['id']) for r in rows}) != len(rows):
        raise ValueError('human audit IDs missing or duplicated')
    for row in rows:
        if expected.get((row['split'], row['id'])) != row['pair_sha256']:
            raise ValueError('human audit provenance mismatch')
        if not row['reviewer'].strip() or row['verdict'].strip() != 'supported':
            raise ValueError('human audit pending/rejected; review source, dates, numbers, entities and meaning first')


def reserve_split(article_id):
    key = hashlib.sha256((PROTOCOL+'/reserve/1337/'+article_id).encode()).digest()
    return 'val' if int.from_bytes(key, 'big') < (1 << 256)//20 else 'train'


def extend_pairs(rows, parts, seen, tok):
    counts = Counter()
    if len(parts['val']) >= VAL_COUNT:
        return dict(counts)
    for index, raw in enumerate(rows):
        counts['raw_rows_scanned'] += 1
        row = record(raw)
        if row is None:
            counts['invalid_editorial_record'] += 1
        elif row['id'] in seen:
            counts['duplicate_or_frozen_id'] += 1
        else:
            seen.add(row['id'])
            item, reason = screen_pair(row, tok)
            if item is None:
                counts[reason] += 1
            else:
                split = reserve_split(row['id'])
                parts[split].append({**item, 'reserve_raw_row': index})
                counts['accepted_'+split] += 1
                if len(parts['val']) >= VAL_COUNT:
                    break
        if (index+1) % 20000 == 0:
            print('RESERVE', index+1, 'train/val', len(parts['train']), len(parts['val']), flush=True)
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--vocab', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--reserve-parquet')
    parser.add_argument('--frozen-id-index', help='Existing frozen prediction JSONL; only its ID field is used for deduplication')
    args = parser.parse_args()
    if bool(args.reserve_parquet) != bool(args.frozen_id_index):
        parser.error('reserve parquet and frozen ID index must be provided together')
    data, out = Path(args.data), Path(args.output)
    parent = json.loads((data/'news_manifest.json').read_text(encoding='utf-8'))
    tok = BPETokenizer.load(args.vocab)
    assert tok.vocab_size == 8192
    out.mkdir(parents=True, exist_ok=False)
    parts, counts, audits = {}, {}, []
    seen = set()
    for split in ('train', 'val'):
        path = data/f'news_{split}.json'
        assert file_checksum(str(path)) == parent['splits'][split]['sha1']
        rows = json.loads(path.read_text(encoding='utf-8'))
        assert len(rows) == parent['splits'][split]['count']
        accepted, reasons = [], Counter()
        for index, row in enumerate(rows):
            assert row['id'] not in seen
            seen.add(row['id'])
            item, reason = screen_pair(row, tok)
            if item is None:
                reasons[reason] += 1
            else:
                accepted.append({**item, 'original_index': index})
            if (index+1) % 10000 == 0:
                print(split, index+1, 'accepted', len(accepted), flush=True)
        assert len(accepted)+sum(reasons.values()) == len(rows)
        parts[split] = accepted
        counts[split] = {'input': len(rows), 'accepted': len(accepted), 'first_rejection_reason': dict(reasons)}
        del rows
        print(split, json.dumps(counts[split]), flush=True)
    reserve = None
    if args.reserve_parquet:
        import pyarrow.parquet as pq

        raw, index = Path(args.reserve_parquet), Path(args.frozen_id_index)
        assert file_checksum(str(raw)) == parent['raw_files'][raw.name]
        with index.open(encoding='utf-8') as source:
            frozen_ids = [json.loads(line)['id'] for line in source if line.strip()]
        assert len(frozen_ids) == len(set(frozen_ids)) == parent['splits']['test']['count']
        assert not seen & set(frozen_ids)
        seen.update(frozen_ids)
        batches = pq.ParquetFile(raw).iter_batches(batch_size=1024, columns=['title','summary','content'])
        reserve = {'raw_file': str(raw), 'raw_sha1': parent['raw_files'][raw.name],
                   'frozen_id_index': str(index), 'frozen_id_index_sha1': file_checksum(str(index)),
                   'frozen_ids_used_only_for_dedup': len(frozen_ids),
                   'split': 'novel IDs only; sha256(protocol/reserve/1337/ID) lowest5% ->val; preserve original ID splits',
                   'stop': 'first64 accepted validation IDs before hash-order selection; no model outputs used',
                   'counts': extend_pairs((r for b in batches for r in b.to_pylist()), parts, seen, tok)}
        assert not {r['id'] for rows in parts.values() for r in rows} & set(frozen_ids)
    for split, accepted in parts.items():
        # Fixed hash order, independent of any model prediction or rating.
        accepted.sort(key=lambda r: hashlib.sha256((PROTOCOL+r['id']).encode()).hexdigest())
        for row in accepted[:32 if split == 'train' else 16]:
            audits.append({'split': split, 'id': row['id'], 'pair_sha256': pair_sha(row)})
        (out/f'news_{split}.json').write_text(json.dumps(accepted, ensure_ascii=False), encoding='utf-8')
    manifest = {
        'protocol': PROTOCOL, 'seed': 1337, 'parent': parent, 'parent_directory': str(data),
        'license': parent['license'], 'context': CONTEXT, 'output_tokens': OUTPUT_TOKENS,
        'asr_cer': CER, 'noise': 'legacy measured-CER synthetic corruption; seed=int(article ID[:8],16); not calibrated to video',
        'source': 'unchanged editorial article body for all3 formats; uppercase-only bodies lowered as in serving',
        'labels': 'human-authored editorial sapo and headline, no generated labels; caption uses headline surrogate',
        'screening': 'complete sapo; both targets <=95 BPE; all target words/numeric spans in body; entire clean+ASR input fits all3 formats; no truncation',
        'publisher_cleaning_regex': PUBLISHER_PREFIX.pattern, 'original_split_screen_counts': counts, 'reserve': reserve,
        'screening_revision': 'sentence-ending-v2-reject-terminal-ellipsis',
        'vocab_sha1': file_checksum(args.vocab),
        'splits': {s: {'count': len(r), 'sha1': file_checksum(str(out/f'news_{s}.json'))} for s,r in parts.items()},
        'validation_ids': [r['id'] for r in parts['val'][:VAL_COUNT]],
        'selection': 'mean clean+ASR sum ROUGE-L on same64 validation IDs; title/cap regression only; no test selection',
        'audit_sample': audits, 'human_audit': 'PENDING - blank annotations; trainer refuses until sample is supported',
        'test_data_opened': False, 'frozen_video_data_used': False,
        'validation_required_n': VAL_COUNT,
        'status': 'SCREENED_CANDIDATES_HUMAN_AUDIT_PENDING' if len(parts['val']) >= VAL_COUNT
                  else 'SCREENED_CANDIDATES_INSUFFICIENT_VALIDATION_AND_HUMAN_AUDIT_PENDING',
    }
    with (out/'human_audit.csv').open('w', encoding='utf-8-sig', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=['split','id','pair_sha256','reviewer','verdict','notes'])
        writer.writeheader()
        writer.writerows(audits)
    texts = ['HUMAN AUDIT: read the whole source; check names, quantities, dates, negation and claimed relations.',
             'Review BOTH summary and title; only enter supported in human_audit.csv if both are supported.',
             'Blank/pending/reject blocks training. Do not sign model-generated judgments as human review.\n']
    for audit in audits:
        row = next(r for r in parts[audit['split']] if r['id']==audit['id'])
        texts.append(f"{audit['split']} / {row['id']}\nTITLE: {row['title']}\nSUMMARY: {row['summary']}\nSOURCE: {row['body']}\n")
    (out/'human_audit.txt').write_text('\n'.join(texts), encoding='utf-8')
    (out/'news_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PREPARATION_COMPLETE', out, manifest['status'], flush=True)


if __name__ == '__main__':
    main()
