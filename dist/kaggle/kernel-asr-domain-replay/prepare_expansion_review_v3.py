"""AI-02b re-review: compact, prioritised ASR review page after the v2 export confirmed 57/60 Whisper drafts unchanged.

Verification is disabled until the clip's WAV has played to the end; the export records audio_played_full per clip.
Prefill = Claude text-only proposal when it differs from the draft (still needs listening); the Whisper draft stays visible.
"""
import json

from prepare_expansion import OUT, save, sha
from prepare_expansion_review import render

V2 = OUT / 'asr_review_v2/packet.json'
RECEIVED = OUT / 'received_87a7eb6fd111/asr_expansion_review_v2.json'
PROPOSALS = OUT / 'claude_proposals_v1/asr_claude_proposals_v1.json'
PROTOCOL = 'asr-expansion-review-v3'
TIER = {'EXCLUDE_CANDIDATE': 1, 'CORRECTION': 2, 'LISTEN_ONLY': 3}
HINT = {1: 'Ưu tiên 1 — nghi Whisper ảo giác/lặp: nếu chỉ có nhạc hoặc không có lời, ghi lý do loại và KHÔNG xác nhận.',
        2: 'Ưu tiên 2 — ô lời chép đã điền gợi ý sửa của Claude (Claude không nghe audio): nghe và sửa đúng từng từ.',
        3: 'Ưu tiên 3 — nháp méo nặng hoặc chưa có gợi ý: chép lại theo audio, hoặc ghi lý do nếu không nghe rõ.'}


def make_packet(v2, received, proposals, received_sha):
    assert received['packet_sha256'] == v2['packet_sha256']
    drafts = {s['sample_id']: s['initial_transcript'].strip() for s in v2['samples']}
    done = {r['sample_id'] for r in received['records']
            if r['transcript_verified'] is True and r['transcript'].strip() != drafts[r['sample_id']]}
    prop = {r['sample_id']: r for r in proposals['records']}
    rows = []
    for s in v2['samples']:
        sid = s['sample_id']
        if sid in done:
            continue
        p = prop[sid]
        assert p['audio_sha256'] == s['audio_sha256']
        changed = p['action'] == 'CORRECTION' and p['changed_from_draft']
        tier = 2 if changed else 3 if p['action'] == 'CORRECTION' else TIER[p['action']]
        notes = '; '.join(p['uncertain']) or 'không'
        terms = ', '.join(p['term_hints']) or 'không'
        rows.append({**s, 'initial_transcript': p['proposed_transcript'] if changed else s['initial_transcript'],
                     'whisper_draft': s['initial_transcript'], 'tier': tier,
                     'prior_feedback': f"{HINT[tier]} {s['prior_feedback']} Chỗ cần nghe kỹ: {notes}. Thuật ngữ gợi ý: {terms}.",
                     'transcript_verified': False})
    rows.sort(key=lambda r: (r['tier'], r['sample_id']))
    return {'protocol': PROTOCOL, 'packet_sha256': v2['packet_sha256'], 'source_review_sha256': received_sha,
            'annotator': received['annotator'], 'accepted_from_v2': sorted(done), 'samples': rows}


def render_v3(packet):
    html = render(packet)
    changes = {
        "const key='asr-expansion-review-v2-'": "const key='asr-expansion-review-v3-'",
        "a.download='asr_expansion_review_v2.json'": "a.download='asr_expansion_review_v3.json'",
        '60 đoạn train mới, mỗi đoạn 20 giây. Đây là bản nháp WhisperWeb chưa được xác minh; hãy nghe WAV và đối chiếu video.':
            'Duyệt lại các đoạn chưa sửa ở lần trước, xếp theo ưu tiên. Ô xác nhận chỉ bật sau khi audio WAV của đoạn đó đã phát hết. '
            'Có thể dừng giữa chừng và xuất JSON; đoạn chưa xác nhận vẫn để chờ.',
        '<summary>Bản nháp WhisperWeb nguyên văn</summary><p class="note">${esc(r.initial_transcript)}</p>':
            '<summary>Bản nháp WhisperWeb nguyên văn</summary><p class="note">${esc(r.whisper_draft)}</p>',
        "<h2>${esc(r.sample_id)} · ": "<h2>Ưu tiên ${r.tier} · ${esc(r.sample_id)} · ",
        "transcript_verified:verified,origin:": "transcript_verified:verified,audio_played_full:played.has(r.sample_id),origin:",
        "   if(!annotator.value.trim())invalid=":
            "   if(!played.has(card.dataset.id))invalid=[check,'Hãy nghe hết audio WAV của đoạn này trước khi xác nhận.'];\n"
            "   else if(!annotator.value.trim())invalid=",
        "document.querySelector('#status').textContent=counts(collect());":
            "const played=new Set(state.played||[]);\n"
            "document.addEventListener('ended',e=>{const c=e.target.closest&&e.target.closest('article');"
            "if(e.target.tagName==='AUDIO'&&c){played.add(c.dataset.id);state.played=[...played];"
            "try{localStorage.setItem(key,JSON.stringify(state));}catch{}}},true);\n"
            "document.querySelector('#status').textContent=counts(collect());",
        "state={annotator:value.annotator,rows:": "state={played:[...played],annotator:value.annotator,rows:",
    }
    for old, new in changes.items():
        assert html.count(old) == 1, f'review form changed: {old[:60]}'
        html = html.replace(old, new)
    return html


def main():
    target = OUT / 'asr_review_v3'
    assert not target.exists(), 'never overwrite human review work'
    v2 = json.loads(V2.read_text(encoding='utf-8'))
    received = json.loads(RECEIVED.read_text(encoding='utf-8-sig'))
    proposals = json.loads(PROPOSALS.read_text(encoding='utf-8'))
    packet = make_packet(v2, received, proposals, sha(RECEIVED))
    target.mkdir()
    save(target / 'packet.json', packet)
    with (target / 'index.html').open('x', encoding='utf-8') as stream:
        stream.write(render_v3(packet))
    tiers = {t: sum(r['tier'] == t for r in packet['samples']) for t in (1, 2, 3)}
    report = {'status': 'RE_REVIEW_READY', 'reason': 'v2 export confirmed 57/60 Whisper drafts unchanged incl. hallucination stubs',
              'clips': len(packet['samples']), 'tiers': tiers, 'accepted_from_v2': packet['accepted_from_v2'],
              'received_v2_sha256': packet['source_review_sha256'], 'packet_sha256': sha(target / 'packet.json'),
              'index_sha256': sha(target / 'index.html'), 'training_ready': False}
    save(target / 'preparation.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
