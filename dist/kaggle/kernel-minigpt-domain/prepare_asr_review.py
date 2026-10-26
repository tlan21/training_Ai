"""Continue the received human edits; separate ASR attestation from summary authoring."""
import json
from pathlib import Path

from build_packet import render
from prepare_media import ROOT, OUT, sha, save


def make_packet(samples, review, packet_sha, review_sha):
    assert review['packet_sha256'] == packet_sha
    records = {r['sample_id']: r for r in review['records']}
    assert len(records) == len(review['records']) == len(samples)
    assert set(records) == {r['sample_id'] for r in samples}
    rows = []
    for sample in samples:
        row = records[sample['sample_id']]
        assert all(row[k] == sample[k] for k in ('audio_sha256', 'video_sha256'))
        rows.append({**sample, 'video_src': '../' + sample['video'], 'initial_transcript': row['transcript'],
                     'prior_feedback': row['reject_reason'], 'speaker_id': row.get('speaker_id', ''),
                     'transcript_verified': False})
    rows.sort(key=lambda row: row['split'] != 'val')
    return {'protocol': 'asr-verbatim-v1', 'packet_sha256': packet_sha,
            'source_review_sha256': review_sha, 'annotator': review['annotator'], 'samples': rows}


def main():
    target = OUT / 'asr_verbatim_v1'
    assert not target.exists(), 'never overwrite human drafts or a prepared packet'
    received = OUT / 'whisper_review_v1/received_860f8068d0bd/reviewed_whisper_domain_v1.json'
    assert sha(received) == '860f8068d0bd16398bbf1d2fd99bc24e276e01c55ca6b5343c78df757ca9e5a4'
    manifest = json.loads((ROOT / 'data/manifests/minigpt_real_domain.json').read_text(encoding='utf-8'))
    samples = json.loads((OUT / 'samples.json').read_text(encoding='utf-8'))
    assert sha(OUT / 'samples.json') == manifest['samples_sha256']
    guard = json.loads((ROOT / 'data/manifests/asr_three_source_real_audio.json').read_text(encoding='utf-8'))['protected_hashes']
    for sample in samples:
        assert all(sha(OUT / sample[k]) == sample[k + '_sha256'] for k in ('audio', 'video'))
    assert all(sha(p) == digest for p, digest in guard.items())
    review = json.loads(received.read_text(encoding='utf-8'))
    packet = make_packet(samples, review, manifest['samples_sha256'], sha(received))
    target.mkdir()
    save(target / 'packet.json', packet)
    (target / 'index.html').write_text(render(packet), encoding='utf-8')
    blank = {'protocol': packet['protocol'], 'packet_sha256': packet['packet_sha256'],
             'source_review_sha256': packet['source_review_sha256'], 'annotator': packet['annotator'],
             'training_ready': False, 'records': [
                 {k: row[k] for k in ('sample_id', 'audio_sha256', 'video_sha256')} | {
                     'transcript': row['initial_transcript'], 'speaker_id': row['speaker_id'],
                     'prior_feedback': row['prior_feedback'], 'exclude_reason': '', 'transcript_verified': False,
                     'origin': 'EXTERNAL_ASR_DRAFT_UNVERIFIED', 'draft_origin': 'EXTERNAL_ASR_DRAFT_UNVERIFIED'}
                 for row in packet['samples']]}
    save(target / 'asr_verbatim_draft.json', blank)
    assert all(sha(p) == digest for p, digest in guard.items())
    report = {'status': 'ASR_REVIEW_PREPARED_WORD_LEVEL_ATTESTATION_PENDING', 'directory': str(target),
              'packet_sha256': sha(target / 'packet.json'), 'source_review_sha256': sha(received),
              'index_sha256': sha(target / 'index.html'), 'seed_export_sha256': sha(target / 'asr_verbatim_draft.json'),
              'transcripts_preserved': len(samples), 'prior_feedback_preserved': sum(bool(r['prior_feedback']) for r in packet['samples']),
              'validation_first': 10, 'train': 30, 'asr_specific_confirmations_created': 0,
              'old_combined_checkbox_is_not_asr_completion_evidence': True, 'training_started': False,
              'audio_listening_capability': 'No direct audio-input/listening tool available in this session',
              'protected_hashes': guard}
    save(target / 'preparation.json', report)
    save(ROOT / 'data/manifests/asr_verbatim_preparation.json', report)
    print('SEEDED40TRANSCRIPTS/33FEEDBACK;ASR-ONLY0ATTESTATIONS;VALIDATION10FIRST;NO GOLD/TRAINING CREATED')


if __name__ == '__main__':
    main()
