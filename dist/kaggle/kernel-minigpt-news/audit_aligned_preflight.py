"""Mechanical source evidence and label defects; never fill human verdicts or generate targets."""
import collections
import csv
import difflib
import json
import re
import sys
from pathlib import Path

from transcribe_pretrained_drafts import ROOT, sha, save

sys.path.insert(0,str(ROOT/'ai-core'))
from ai_core.scripts.prepare_aligned_summary import has_sentence_ending, pair_sha
from ai_core.scripts.finetune_news_summary import validate_aligned_bundle

BASE = Path('D:/data_training_ai/minigpt_news/aligned_summary_v1_reserve_20261019')
OUT = Path('D:/data_training_ai/minigpt_news/aligned_summary_preflight_20261019')


def words(text):
    return re.findall(r'\w+',text.casefold())


def source_span(source,label):
    spans = list(re.finditer(r'\w+',source))
    match = difflib.SequenceMatcher(None,words(label),[m.group().casefold() for m in spans],autojunk=False).find_longest_match()
    start = spans[match.b].start() if match.size else 0
    end = spans[match.b+match.size-1].end() if match.size else 0
    return {'start':start,'end':end,'quote':source[start:end],
            'matched_words':match.size,'target_words':len(words(label))}


def main():
    OUT.mkdir(exist_ok=False)
    manifest = json.loads((BASE/'news_manifest.json').read_text(encoding='utf-8'))
    bundle = json.loads((BASE/'bundle.json').read_text(encoding='utf-8'))
    assert all(sha(BASE/name)==entry['sha256'] for name,entry in bundle['files'].items())
    protected = sha(BASE/'human_audit.csv')
    with (BASE/'human_audit.csv').open(encoding='utf-8-sig',newline='') as stream:
        audit = list(csv.DictReader(stream))
    assert len(audit)==48 and all(not r['reviewer'] and not r['verdict'] for r in audit)
    parts = {s:json.loads((BASE/f'news_{s}.json').read_text(encoding='utf-8')) for s in ('train','val')}
    duplicates = {}
    for field in ('body','summary','title'):
        indexes = {s:collections.Counter(' '.join(words(r[field])) for r in rows) for s,rows in parts.items()}
        duplicates[field] = {'within_train':sum(n-1 for n in indexes['train'].values()),
                             'within_val':sum(n-1 for n in indexes['val'].values()),
                             'shared_train_val':len(indexes['train'].keys() & indexes['val'].keys())}
    invalid = [{'split':s,'id':r['id'],'target':r['summary'],'mechanical_issue':'invalid_sentence_ending'}
               for s,rows in parts.items() for r in rows if not has_sentence_ending(r['summary'])]
    records, text = [], ['MECHANICAL EVIDENCE ONLY. Human support verdicts remain unfilled.\n']
    lookup = {(s,r['id']):r for s,rows in parts.items() for r in rows}
    for i,expected in enumerate(manifest['audit_sample'],1):
        row = lookup[expected['split'],expected['id']]
        assert pair_sha(row)==expected['pair_sha256']
        item = {**expected,'ordinal':i,'title':row['title'],'summary':row['summary'],'source':row['body'],
                'invalid_sentence_ending':not has_sentence_ending(row['summary']),
                'title_span':source_span(row['body'],row['title']),
                'summary_span':source_span(row['body'],row['summary']),
                'semantic_support':'NOT ADJUDICATED',
                'leading_marker':(re.match(r'^\([^)]{1,45}\)|^[A-ZĐ]{2,8}\s*[-–—]',row['summary']) or [''])[0]}
        for key in ('title_span','summary_span'):
            span = item[key]
            assert row['body'][span['start']:span['end']]==span['quote']
        records.append(item)
        text.append(f"{i}. {expected['split']} / {row['id']}\nTITLE: {row['title']}\nSUMMARY: {row['summary']}\n"
                    f"ENDING FLAG: {item['invalid_sentence_ending']}\nLONGEST SOURCE MATCH: {item['summary_span']['quote']}\n"
                    f"FULL SOURCE: {row['body']}\n")
    try:
        validate_aligned_bundle(BASE,manifest,parts['train'],parts['val'])
    except ValueError as e:
        assert 'summaries have invalid sentence endings' in str(e)
        gate = str(e)
    else:
        raise AssertionError('old packet should fail the corrected ending guard')
    log = Path('D:/data_training_ai/minigpt_news/aligned_summary_preflight_sanity_20261019.log')
    checks = [line for line in log.read_text(encoding='utf-8').splitlines() if line.startswith('SANITY ')]
    assert len(checks)==4 and all('PASS' in line for line in checks)
    report = {'status':'MECHANICAL_AUDIT_DONE_V1_TRAINING_REFUSED_HUMAN_AUDIT_PENDING',
              'base':str(BASE),'base_manifest_sha256':sha(BASE/'news_manifest.json'),
              'human_audit_sha256':protected,'human_annotations_filled':0,'duplicates':duplicates,
              'invalid_sentence_endings':invalid,'invalid_counts':dict(collections.Counter(r['split'] for r in invalid)),
              'old_packet_gate':gate,'sanity_checks':checks,'sanity_log_sha256':sha(log),
              'script_sha256':sha(Path(__file__)),'records':records}
    save(OUT/'preflight_v1.json',report)
    (OUT/'source_evidence_48.txt').write_text('\n'.join(text),encoding='utf-8')
    assert sha(BASE/'human_audit.csv')==protected
    assert all(sha(BASE/name)==entry['sha256'] for name,entry in bundle['files'].items())
    print('COMPLETE',report['invalid_counts'],gate,flush=True)


if __name__=='__main__':
    main()
