"""Audit the user's single-file submission; never invent separate rater records."""

import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[3]


def summarize(rows, expected):
    assert len(rows) == len(expected) == 30
    assert {row['sample_id'] for row in rows} == expected, 'missing/duplicate sample IDs'
    column = 'overall_score_1_to_5'
    if all(not row[column].strip() for row in rows):
        column = 'notes'
    values = [row[column].strip() for row in rows]
    assert all(value in {'1', '2', '3', '4', '5'} for value in values), '30 integer scores1–5 required'
    scores = [int(value) for value in values]
    return {'source_score_column': column, 'observed_score_records': len(scores),
            'mean': mean(scores), 'threshold': 3, 'threshold_pass': mean(scores) >= 3,
            'score_counts': {str(i): Counter(scores)[i] for i in range(1, 6)},
            'samples_at_least_3': sum(score >= 3 for score in scores),
            'sample_scores': {row['sample_id']: score for row, score in zip(rows, scores)}}


def main():
    manifest = json.loads((ROOT / 'data/manifests/minigpt_real_video.json').read_text(encoding='utf-8'))
    packet = Path(manifest['packet'])
    samples = packet / 'samples.json'
    assert hashlib.sha256(samples.read_bytes()).hexdigest() == manifest['samples_sha256'], 'frozen samples changed'
    expected = {row['sample_id'] for row in json.loads(samples.read_text(encoding='utf-8'))}
    source = packet / 'ratings_rater_1.csv'
    original = source.read_bytes()
    checksum = hashlib.sha256(original).hexdigest()
    with source.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    result = summarize(rows, expected)
    submission = packet / ('human_submission_' + checksum[:12])
    submission.mkdir(exist_ok=True)
    backup = submission / 'ratings_rater_1_original.csv'
    if backup.exists():
        assert backup.read_bytes() == original, 'refusing to overwrite original submission'
    else:
        shutil.copy2(source, backup)
    normalized = submission / 'ratings_normalized.csv'
    if not normalized.exists():
        with normalized.open('w', encoding='utf-8-sig', newline='') as target:
            writer = csv.writer(target)
            writer.writerow(['sample_id', 'overall_score_1_to_5', 'original_notes'])
            writer.writerows((row['sample_id'], result['sample_scores'][row['sample_id']], row['notes']) for row in rows)
    with normalized.open(encoding='utf-8-sig', newline='') as stream:
        normalized_rows = list(csv.DictReader(stream))
    assert len(normalized_rows) == 30, 'normalized submission must contain exactly30 records'
    assert {row['sample_id']: int(row['overall_score_1_to_5']) for row in normalized_rows} == result['sample_scores']
    result.update({'date': '2026-10-15', 'status': 'SHARED HUMAN SUBMISSION EVALUATED',
                   'conclusion': 'BELOW ACCEPTANCE THRESHOLD' if not result['threshold_pass'] else 'REPORTED MEAN MEETS THRESHOLD; THREE-SHEET PROTOCOL UNVERIFIED',
                   'source_file': str(source), 'source_sha256': checksum, 'original_backup': str(backup),
                   'normalized_file': str(normalized), 'samples_sha256': manifest['samples_sha256'],
                   'reported_raters': 3, 'reported_ratings_if_identical': 90,
                   'user_attestation': 'User states all three raters completed evaluation with identical results, stored in ratings_rater_1.',
                   'independent_rater_records_available': False, 'independence_verified': False,
                   'three_separate_sheets_complete': False,
                   'reported_three_rater_mean_if_identical': result['mean'],
                   'scope': 'End-to-end ASR-to-MiniGPT summary quality on30 fixed clips, not accuracy of all6 models.',
                   'limitation': 'Only30 recorded scores in one shared file; cannot independently verify90 original ratings or rater independence. No kappa/CI claimed.'})
    text = json.dumps(result, ensure_ascii=False, indent=2)
    (submission / 'results.json').write_text(text, encoding='utf-8')
    (ROOT / 'docs/T1.6_real_video_shared_human_results.json').write_text(text, encoding='utf-8')
    assert source.read_bytes() == original and backup.read_bytes() == original
    print(text)


if __name__ == '__main__':
    main()
