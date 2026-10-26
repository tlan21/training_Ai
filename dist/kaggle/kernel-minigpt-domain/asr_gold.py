"""Import explicit transcript-only attestations and score the fixed validation set; never train."""
import argparse
import json
import sys
from pathlib import Path

from prepare_media import ROOT, OUT, sha, save
sys.path[:0] = [str(ROOT / 'ai-core'), str(ROOT / 'dist/kaggle/kernel-minigpt-news')]
from ai_core.scripts.prepare_asr_robust import normalize
from diagnose_asr_reference import reference_metrics


def validate(payload, packet):
    if payload.get('test_fixture') is True:
        raise ValueError('synthetic QA fixtures are not human labels')
    if payload.get('protocol') != 'asr-verbatim-v1' or any(payload.get(k) != packet[k] for k in ('packet_sha256', 'source_review_sha256')):
        raise ValueError('wrong/stale ASR packet or received-review hash')
    rows = payload.get('records', [])
    expected = {r['sample_id']: r for r in packet['samples']}
    ids = [r['sample_id'] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError('duplicate/missing/unknown clip IDs; never silently drop clips')
    approved = {'train': [], 'val': []}
    pending = {'train': [], 'val': []}
    for row in rows:
        sample = expected[row['sample_id']]
        sid, split = sample['sample_id'], sample['split']
        if any(row.get(k) != sample[k] for k in ('audio_sha256', 'video_sha256')):
            raise ValueError(f'{sid}: media hash changed')
        if row.get('prior_feedback') != sample['prior_feedback']:
            raise ValueError(f'{sid}: historical feedback changed')
        if type(row.get('transcript_verified')) is not bool or row.get('draft_origin') != 'EXTERNAL_ASR_DRAFT_UNVERIFIED':
            raise ValueError(f'{sid}: ASR-specific attestation/provenance missing')
        verified = row['transcript_verified']
        origin = 'human_reviewed_external_asr' if verified else 'EXTERNAL_ASR_DRAFT_UNVERIFIED'
        if row.get('origin') != origin:
            raise ValueError(f'{sid}: transcript provenance does not match attestation')
        if not verified:
            pending[split].append({'sample_id': sid, 'exclude_reason': row.get('exclude_reason', '')})
            continue
        text = row.get('transcript', '')
        if (not payload.get('annotator', '').strip() or not isinstance(text, str) or not text.strip()
                or row.get('exclude_reason', '').strip()
                or any(marker in text.casefold() for marker in ('[không rõ]', '[inaudible]', '[unclear]'))):
            raise ValueError(f'{sid}: incomplete/unclear transcript, missing reviewer or explicitly excluded')
        approved[split].append({'sample_id': sid, 'path': str(OUT / sample['audio']), 'label': 'vi',
            'split': split, 'group': sample['channel_id'], 'extra': {'source': 'real_domain_user_review',
            'transcript': normalize(text), 'raw_transcription': text, 'audio_sha256': sample['audio_sha256'],
            'video_sha256': sample['video_sha256'], 'video_id': sample['video_id'], 'channel_id': sample['channel_id'],
            'speaker_id': row.get('speaker_id', ''), 'label_origin': origin, 'draft_origin': row['draft_origin'],
            'annotator': payload['annotator'].strip(), 'prior_feedback': sample['prior_feedback']}})
    for key in ('video_id', 'channel_id', 'speaker_id'):
        left = {r['extra'][key] for r in approved['train'] if r['extra'][key]}
        right = {r['extra'][key] for r in approved['val'] if r['extra'][key]}
        if left & right:
            raise ValueError(f'{key} overlaps train/validation')
    return approved, pending


def score_validation(approved, packet, comparison):
    expected = {r['sample_id'] for r in packet['samples'] if r['split'] == 'val'}
    if {r['sample_id'] for r in approved['val']} != expected:
        return None
    outputs = {r['sample_id']: r for r in comparison['records']}
    if len(outputs) != len(comparison['records']):
        raise ValueError('duplicate prediction IDs')
    result = {}
    for variant, checkpoint in comparison['checkpoints'].items():
        rows = []
        for reference in approved['val']:
            sid = reference['sample_id']
            source = outputs[sid]
            if source['audio_sha256'] != reference['extra']['audio_sha256'] or source['outputs'][variant]['checkpoint_sha256'] != checkpoint:
                raise ValueError('prediction media/checkpoint binding changed')
            rows.append({'sample_id': sid, 'reference': reference['extra']['transcript'],
                         'asr': {'full_transcript': source['outputs'][variant]['text']}})
        result[variant] = {**reference_metrics(rows), 'checkpoint_sha256': checkpoint, 'predictions': rows,
            'normalization': 'NFC/uppercase/whitespace-collapse references; raw production uppercase CTC output, CER includes spaces'}
    return result


def freeze_validation(path, references):
    identity = [{'sample_id': r['sample_id'], 'audio_sha256': r['extra']['audio_sha256'],
                 'transcript': r['extra']['transcript']} for r in sorted(references, key=lambda r: r['sample_id'])]
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != identity:
            raise ValueError('validation references already frozen; use a new version for corrections')
    else:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(identity, stream, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', required=True, type=Path)
    args = parser.parse_args()
    base = OUT / 'asr_verbatim_v1'
    prep = json.loads((base / 'preparation.json').read_text(encoding='utf-8'))
    assert sha(base / 'packet.json') == prep['packet_sha256']
    packet = json.loads((base / 'packet.json').read_text(encoding='utf-8'))
    assert sha(OUT / 'samples.json') == packet['packet_sha256']
    assert all(sha(p) == v for p, v in prep['protected_hashes'].items())
    assert all(sha(OUT / row[k]) == row[k + '_sha256'] for row in packet['samples'] for k in ('audio', 'video'))
    payload = json.loads(args.labels.read_text(encoding='utf-8-sig'))
    try:
        approved, pending = validate(payload, packet)
    except ValueError as error:
        parser.exit(1, f'NOT ASR GOLD READY: {error}\n')
    pilot = json.loads((ROOT / 'data/manifests/asr_three_source_real_audio.json').read_text(encoding='utf-8'))
    comparison_path = Path(pilot['packet']) / 'comparison.json'
    assert sha(comparison_path) == pilot['output_hashes']['comparison.json']
    comparison = json.loads(comparison_path.read_text(encoding='utf-8'))
    scores = score_validation(approved, packet, comparison)
    vocab = json.loads(Path('D:/data_training_ai/asr_robust/kaggle_dataset/robust_vocab.json').read_text(encoding='utf-8'))['chars']
    unsupported = [{'sample_id': r['sample_id'], 'characters': sorted(set(r['extra']['transcript']) - set(vocab))}
                   for r in approved['train'] if set(r['extra']['transcript']) - set(vocab)]
    expected_counts = {split: sum(r['split'] == split for r in packet['samples']) for split in ('train', 'val')}
    complete = all(len(approved[s]) == expected_counts[s] for s in expected_counts)
    report = {'status': 'USER_ATTESTED_REFERENCES_IMPORTED' if any(approved.values()) else 'ASR_ATTESTATION_PENDING_NO_GOLD_IMPORTED',
        'source_labels_sha256': sha(args.labels), 'source_review_sha256': packet['source_review_sha256'],
        'counts': {s: len(approved[s]) for s in approved}, 'expected_counts': expected_counts, 'pending': pending,
        'train_unsupported_labels': unsupported, 'training_ready': complete and not unsupported,
        'validation_scores': scores, 'training_started': False, 'checkpoint_deployed': False,
        'label_attestation': 'User-supplied word-level/audio attestation; not an independent semantic/audio audit',
        'validation_scope': 'Fixed10 previously inspected domain validation clips, not an independent final test',
        'summary_labels_imported': False}
    if any(approved.values()):
        if scores is not None:
            freeze_validation(base / 'frozen_validation.json', approved['val'])
        target = base / ('accepted_asr_' + sha(args.labels)[:12])
        target.mkdir(exist_ok=False)
        for split, rows in approved.items():
            save(target / ('asr_' + split + '.json'), {'meta': {k: v for k, v in report.items() if k != 'validation_scores'}, 'items': [
                {k: v for k, v in row.items() if k != 'sample_id'} for row in rows]})
        save(target / 'provenance_and_scores.json', report)
        report['directory'] = str(target)
    assert all(sha(p) == v for p, v in prep['protected_hashes'].items())
    save(base / ('intake_' + sha(args.labels)[:12] + '.json'), report)
    save(ROOT / 'data/manifests/asr_verbatim_intake.json', report)
    print(report['status'], report['counts'], 'SCORED', scores is not None, 'NO TRAINING/DEPLOYMENT')


if __name__ == '__main__':
    main()
