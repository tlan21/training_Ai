"""Reuse the ASR-only form for new machine-assisted train drafts; never approve labels."""
import json
from pathlib import Path

from prepare_expansion import ROOT, OUT, save, sha

TEMPLATE = ROOT / 'dist/kaggle/kernel-minigpt-domain/asr_review.html'
PROTOCOL = 'asr-expansion-review-v2'


def make_packet(samples, sources, drafts, samples_sha, drafts_sha):
    assert drafts['packet_sha256'] == samples_sha
    assert drafts['human_verified'] is False and drafts['training_ready'] is False
    by_id = {r['sample_id']: r for r in drafts['records']}
    assert len(by_id) == len(drafts['records']) == len(samples)
    assert set(by_id) == {r['sample_id'] for r in samples}
    by_source = {r['video_id']: r for r in sources}
    rows = []
    for sample in samples:
        draft = by_id[sample['sample_id']]
        assert sample['split'] == 'train'
        assert draft['split'] == sample['split']
        assert all(draft[k] == sample[k] for k in ('audio_sha256', 'video_sha256'))
        assert draft['human_verified'] is False and draft['origin'] == 'EXTERNAL_ASR_DRAFT_UNVERIFIED'
        assert isinstance(draft['transcript'], str)
        source = by_source[sample['video_id']]
        assert source['sha256'] == sample['source_sha256']
        rows.append({**sample, 'source_title': source['title'], 'video_src': '../' + sample['video'],
                     'audio_src': '../' + sample['audio'], 'initial_transcript': draft['transcript'],
                     'prior_feedback': 'Cờ kiểm tra máy: ' + ', '.join(draft['review_flags']) if draft['review_flags'] else 'Chưa có cờ máy; vẫn cần nghe và sửa toàn bộ đoạn.',
                     'speaker_id': '', 'transcript_verified': False})
    return {'protocol': PROTOCOL, 'packet_sha256': samples_sha, 'source_review_sha256': drafts_sha,
            'annotator': '', 'samples': rows}


def render(packet):
    template = TEMPLATE.read_text(encoding='utf-8')
    changes = {
        'Giữ nguyên transcript bạn đã sửa. 10 clip validation ở trước, tiếp theo là 30 clip train.':
            '60 đoạn train mới, mỗi đoạn 20 giây. Đây là bản nháp WhisperWeb chưa được xác minh; hãy nghe WAV và đối chiếu video.',
        'Nguồn nháp Whisper và ghi chú cũ được giữ lại.':
            'Nguồn nháp WhisperWeb và các cờ máy được giữ lại. Ghi ngôn ngữ thực tế: vi, en hoặc mixed; không suy từ metadata nguồn.',
        "const key='asr-verbatim-v1-'": "const key='asr-expansion-review-v2-'",
        'return {protocol:packet.protocol,': 'return {test_fixture:packet.test_fixture===true,protocol:packet.protocol,',
        'Ghi chú bạn đã gửi:': 'Cảnh báo bản nháp:',
        'Bản transcript bạn gửi trước đó': 'Bản nháp WhisperWeb nguyên văn',
        '${r.start_seconds+r.duration_seconds}s': '${Number((r.start_seconds+r.duration_seconds).toFixed(3))}s',
        "return ['val','train'].map": "return ['train'].map",
        "a.download='asr_verbatim_domain_v1.json'": "a.download='asr_expansion_review_v2.json'",
        '<video controls preload="none" src="${esc(r.video_src)}"></video>':
            '<video controls preload="none" src="${esc(r.video_src)}"></video><p>Audio WAV dùng để chép lời:</p><audio controls preload="none" src="${esc(r.audio_src)}" aria-label="Audio WAV của ${esc(r.sample_id)}"></audio>',
        '<label>Mã người nói nếu biết<input class="speaker_id"></label>':
            '<label>Ngôn ngữ đã nghe<select class="language_verified" aria-describedby="error-${i}"><option value="">Chưa xác minh</option><option value="vi">Tiếng Việt (vi)</option><option value="en">Tiếng Anh (en)</option><option value="mixed">Xen Việt / Anh (mixed)</option></select></label><label>Mã người nói nếu biết<input class="speaker_id"></label>',
        "card.querySelector('.speaker_id').value=row.speaker_id??sample.speaker_id??'';":
            "card.querySelector('.speaker_id').value=row.speaker_id??sample.speaker_id??'';card.querySelector('.language_verified').value=row.language_verified??'';",
        "speaker_id:c.querySelector('.speaker_id').value.trim(),":
            "speaker_id:c.querySelector('.speaker_id').value.trim(),language_verified:c.querySelector('.language_verified').value,",
        "else if(reason.value.trim())invalid=":
            "else if(!['vi','en','mixed'].includes(card.querySelector('.language_verified').value))invalid=[card.querySelector('.language_verified'),'Hãy chọn ngôn ngữ đã nghe trước khi xác nhận.'];\n   else if(reason.value.trim())invalid=",
        '</style>': 'audio{width:100%}select{display:block;width:100%;min-height:48px;padding:12px;font:inherit;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--text)}</style>',
    }
    for old, new in changes.items():
        assert template.count(old) == 1, f'ASR form changed: {old}'
        template = template.replace(old, new)
    assert template.count('__PACKET__') == 1
    return template.replace('__PACKET__', json.dumps(packet, ensure_ascii=False).replace('<', '\\u003c'))


def main():
    target = OUT / 'asr_review_v2'
    assert not target.exists(), 'never overwrite human review work'
    preparation = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    source = OUT / 'whisperweb_drafts_v3'
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'DONE_DRAFTS_HUMAN_REVIEW_REQUIRED'
    samples = json.loads((OUT / 'samples.json').read_text(encoding='utf-8'))
    sources = json.loads((OUT / 'sources.json').read_text(encoding='utf-8'))
    drafts = json.loads((source / 'drafts.json').read_text(encoding='utf-8'))
    assert sha(OUT / 'samples.json') == preparation['samples_sha256'] == manifest['packet_sha256']
    assert sha(OUT / 'sources.json') == preparation['sources_sha256']
    assert sha(source / 'drafts.json') == manifest['drafts_sha256']
    assert len(samples) == 60 and len(manifest['jobs']) == 60
    assert [r['sample_id'] for r in samples] == [r['sample_id'] for r in manifest['jobs']]
    for sample in samples:
        assert all(sha(OUT / sample[k]) == sample[k + '_sha256'] for k in ('audio', 'video'))
    for job in manifest['jobs']:
        assert job['status'] == 'DRAFT_EXPORTED_REVIEW_REQUIRED'
        assert {f['file'] for f in job['outputs']} == {job['sample_id'] + '.' + ext for ext in ('txt', 'json', 'srt')}
        assert all(sha(source / f['file']) == f['sha256'] for f in job['outputs'])
    assert all(sha(p) == h for p, h in preparation['protected_hashes'].items())
    packet = make_packet(samples, sources, drafts, sha(OUT / 'samples.json'), sha(source / 'drafts.json'))
    target.mkdir()
    save(target / 'packet.json', packet)
    with (target / 'index.html').open('x', encoding='utf-8') as stream:
        stream.write(render(packet))
    report = {'status': 'REVIEW_READY_HUMAN_WORD_CONFIRMATION_PENDING', 'directory': str(target),
              'clips': 60, 'approved_labels': 0, 'training_ready': False, 'training_started': False,
              'packet_sha256': sha(target / 'packet.json'), 'index_sha256': sha(target / 'index.html'),
              'source_drafts_sha256': packet['source_review_sha256'], 'protected_hashes': preparation['protected_hashes']}
    save(target / 'preparation.json', report)
    save(ROOT / 'data/manifests/asr_expansion_review_v2.json', report)
    print('REVIEW_READY_60_TRAIN_DRAFTS_ZERO_APPROVALS')


if __name__ == '__main__':
    main()
