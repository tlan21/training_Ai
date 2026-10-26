"""Three frozen clips, paired project ASR checkpoints and one unchanged MiniGPT."""
import csv
import html
import json
import sys
import time
import unicodedata
from pathlib import Path

from diagnose_asr_reference import reference_metrics
from transcribe_pretrained_drafts import BASE, IDS, ROOT, save, sha

OUT = BASE / 'asr_candidate_comparison_3_20261019'
CANDIDATE = Path('D:/data_training_ai/asr_robust/outputs-v2/asr_robust_run/asr_ctc/best.pt')


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC', text).upper().split())


def human_metrics(records, references):
    refs = {r['sample_id']: r for r in references}
    assert len(refs) == len(references), 'duplicate reference IDs'
    assert [r['sample_id'] for r in records] == IDS
    missing = [sid for sid in IDS if not refs.get(sid, {}).get('reference', '').strip()
               or not refs.get(sid, {}).get('transcriber', '').strip()]
    result = {'verified_count': 3-len(missing), 'missing_ids': missing, 'baseline': None, 'candidate': None,
              'status': 'PENDING_HUMAN_REFERENCES' if missing else 'HUMAN_REFERENCE_METRICS_READY'}
    if not missing:
        for variant in ('baseline', 'candidate'):
            rows = [{'reference': normalized(refs[r['sample_id']]['reference']),
                     'asr': {'full_transcript': normalized(r[variant]['asr']['full_transcript'])}} for r in records]
            result[variant] = reference_metrics(rows)
            result[variant]['normalization'] = 'NFC uppercase/collapse whitespace; keep punctuation and spaces; no draft labels'
    return result


def review(records, references):
    esc = html.escape
    refs = {r['sample_id']: r for r in references}
    cards = []
    exports = []
    for row in records:
        sid = row['sample_id']
        ref = refs.get(sid, {})
        exports.append({k: row[k] for k in ('sample_id', 'video_id', 'start_seconds', 'duration_seconds', 'audio')})
        columns = []
        for variant, label in [('baseline', 'ASR cũ'), ('candidate', 'ASR candidate mới')]:
            output = row[variant]
            columns.append(f'<section><h3>{label}</h3><p>{esc(output["asr"]["full_transcript"])}</p>'
                           f'<h4>MiniGPT từ transcript này</h4><p>{esc(output["summary"])}</p></section>')
        cards.append(f'<article data-id="{sid}"><h2>{sid} — {esc(row["title"])}</h2>'
                     f'<p>{esc(row["channel"])} · đoạn {row["start_seconds"]}–{row["start_seconds"]+60}s</p>'
                     f'<video controls preload="metadata" src="../evaluation/{esc(row["video"], quote=True)}"></video>'
                     f'<div class="pair">{"".join(columns)}</div>'
                     f'<details><summary>Bản nháp pretrained — CHƯA KIỂM CHỨNG</summary><p>{esc(row["unverified_draft"])}</p></details>'
                     f'<label>Lời chuẩn sau khi nghe (chép đủ 60 giây, không đoán nội dung không nghe rõ)'
                     f'<textarea class="reference" rows="6">{esc(ref.get("reference", ""))}</textarea></label>'
                     f'<label>Người xác nhận<input class="transcriber" value="{esc(ref.get("transcriber", ""), quote=True)}"></label>'
                     '<label class="confirm"><input type="checkbox"> Tôi đã nghe và xác nhận nội dung lời chuẩn ở trên.</label></article>')
    payload = json.dumps(exports, ensure_ascii=False).replace('<', '\\u003c')
    return ('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Đối chiếu ASR candidate — 3 clip</title><style>'
            '*{box-sizing:border-box}body{font:16px system-ui;max-width:1200px;margin:auto;padding:24px;color:#222;background:#fafafa}'
            'p{white-space:pre-wrap;line-height:1.65;overflow-wrap:anywhere}article{margin:24px 0;padding:20px;border:1px solid #ccc;background:white}'
            'video{width:100%;max-height:400px}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}'
            'label{display:block;margin-top:16px}textarea,input:not([type=checkbox]){display:block;width:100%;padding:12px;margin-top:8px;font:inherit;border:1px solid #999}'
            '.confirm{display:flex;gap:10px;align-items:start}button{font:inherit;padding:12px 18px;cursor:pointer}#status{color:#a00000}'
            '@media(max-width:720px){body{padding:12px}.pair{grid-template-columns:1fr}article{padding:14px}}</style>'
            '<h1>ASR cũ / candidate mới → cùng MiniGPT</h1>'
            '<p>Cùng audio, cửa sổ ASR 20s, CPU FP32, MiniGPT temperature=0/max_tokens=96. Không thay model đang phục vụ. '
            'Output là đề xuất của máy; chưa có CER/WER hoặc điểm chất lượng khi thiếu lời chuẩn người xác nhận.</p>'
            '<p>Nghe và sửa lời chuẩn cho cả 3 clip, điền người xác nhận rồi đánh dấu từng ô. '
            'Nút tải chỉ xuất CSV riêng; không sửa references.csv gốc. Lưu file human_references_3.csv và cung cấp đường dẫn để tính metric.</p>'
            + ''.join(cards) + '<button id="export">Tải CSV lời chuẩn 3 mẫu</button><p id="status" role="status"></p><script>'
            f'const rows={payload};'
            '''document.querySelector('#export').onclick=()=>{
 const cards=[...document.querySelectorAll('article')],status=document.querySelector('#status');
 const values=cards.map(c=>({reference:c.querySelector('.reference').value.trim(),transcriber:c.querySelector('.transcriber').value.trim(),confirmed:c.querySelector('[type=checkbox]').checked}));
 if(values.some(v=>!v.reference||!v.transcriber||!v.confirmed)){status.textContent='Cần đủ lời chuẩn, người xác nhận và ô xác nhận cho cả 3 mẫu.';return;}
 const keys=['sample_id','video_id','start_seconds','duration_seconds','audio','reference','transcriber'];
 const quote=v=>String(v).replaceAll('"','""');
 const lines=[keys,...rows.map((r,i)=>keys.map(k=>({...r,...values[i]})[k]))].map(r=>r.map(v=>'"'+quote(v)+'"').join(','));
 const url=URL.createObjectURL(new Blob(['\\ufeff'+lines.join('\\r\\n')],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download='human_references_3.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 status.textContent='Đã xuất CSV riêng. Chưa ghi đè reference gốc hoặc tự tính điểm.';
};</script></html>''')


def main():
    sys.path[:0] = [str(ROOT/'ai-core'), str(ROOT/'inference-service')]
    import torch
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import load_checkpoint
    from app import schemas, services
    from app.registry import registry

    torch.set_num_threads(2)
    torch.manual_seed(1337)
    frozen = BASE/'evaluation/samples.json'
    references = BASE/'asr_ground_truth_30/references.csv'
    manifest = json.loads((ROOT/'data/manifests/minigpt_real_video.json').read_text(encoding='utf-8'))
    assert sha(frozen) == manifest['samples_sha256']
    samples = {r['sample_id']: r for r in json.loads(frozen.read_text(encoding='utf-8'))}
    paths = {'baseline': ROOT/'ai-core/checkpoints/asr_ctc/best.pt', 'candidate': CANDIDATE,
             'minigpt': ROOT/'ai-core/checkpoints/minigpt/best.pt'}
    hashes = {k: sha(p) for k,p in paths.items()}
    assert hashes['baseline'] == manifest['asr_checkpoint_sha256'] and hashes['minigpt'] == manifest['checkpoint_sha256']
    candidate_meta = json.loads((ROOT/'data/manifests/asr_robust_training.json').read_text(encoding='utf-8'))
    assert hashes['candidate'] == candidate_meta['checkpoint_sha256']
    protected = {p: sha(p) for p in [frozen, references, BASE/'evaluation/ratings_rater_1.csv', *paths.values()]}
    with references.open(encoding='utf-8-sig', newline='') as source:
        refs = list(csv.DictReader(source))
    OUT.mkdir(exist_ok=False)

    def load(name):
        saved = load_checkpoint(str(paths[name]))
        model = build_model(saved['config']['name'], ModelConfig(**saved['config'])).eval()
        model.load_state_dict(saved['state_dict'], strict=True)
        return model, saved

    registry.device = 'cpu'
    mini, saved = load('minigpt')
    registry.models['minigpt'] = mini
    registry.minigpt_metadata = saved['metadata']
    registry.tokenizer = registry._rebuild_tokenizer(saved.get('bpe_vocab') or saved['metadata']['bpe_vocab'])
    del saved
    records = []
    for sid in IDS:
        sample = samples[sid]
        for kind in ('audio', 'video'):
            assert sha(BASE/'evaluation'/sample[kind]) == sample[kind+'_sha256']
        draft = json.loads((BASE/'pretrained_drafts_3'/f'{sid}.json').read_text(encoding='utf-8'))
        assert draft['audio_sha256'] == sample['audio_sha256'] and not draft['human_verified']
        records.append({k: sample[k] for k in ('sample_id','video_id','start_seconds','duration_seconds','video','title','channel','source_url','audio_sha256','video_sha256')})
        records[-1].update(audio=str(BASE/'evaluation'/sample['audio']), unverified_draft=draft['draft_text'])
    for variant in ('baseline', 'candidate'):
        model, saved = load(variant)
        registry.models['asr_ctc'] = model
        registry.asr_vocab = saved.get('char_vocab') or saved['metadata']['char_vocab']
        assert len(registry.asr_vocab) == saved['config']['n_chars']
        del saved
        for record in records:
            started = time.monotonic()
            text, segments = services._real_asr(schemas.ASRRequest(audio_url=record['audio'], language='vi'))
            asr_seconds = time.monotonic()-started
            assert text.strip() and all(0 <= s.start_time < s.end_time <= 60.01 for s in segments)
            started = time.monotonic()
            summary = services._real_summarize(schemas.CompletionRequest(prompt=text, max_tokens=96, temperature=0))
            record[variant] = {'asr': {'full_transcript': text, 'segments': [s.model_dump() for s in segments]},
                               'summary': summary, 'asr_seconds': asr_seconds, 'summary_seconds': time.monotonic()-started}
            save(OUT/f'{record["sample_id"]}.json', record)
            print(variant, record['sample_id'], 'ASR chars', len(text), 'summary chars', len(summary), flush=True)
        registry.models.pop('asr_ctc')
        del model
    result = {'status': 'PAIRED OUTPUTS COMPLETE — HUMAN REFERENCES PENDING', 'sample_ids': IDS,
              'checkpoints': hashes, 'device': 'cpu', 'dtype': 'float32', 'torch': torch.__version__,
              'temperature': 0, 'max_tokens': 96, 'asr_window_seconds': 20,
              'services_sha256': sha(ROOT/'inference-service/app/services.py'), 'samples_sha256': sha(frozen),
              'references_sha256': sha(references), 'metrics': human_metrics(records, refs), 'records': records,
              'historical_baseline_exact_text_matches': {r['sample_id']: r['baseline']['asr']['full_transcript'] == samples[r['sample_id']]['asr']['full_transcript'] for r in records},
              'limitation': '3unlabeled clips are a diagnostic, not a quality benchmark. Drafts are not references. Timing is unbalanced CPU diagnostic only.'}
    save(OUT/'comparison.json', result)
    (OUT/'review.html').write_text(review(records, refs), encoding='utf-8')
    assert all(sha(p) == fingerprint for p,fingerprint in protected.items()), 'protected input changed'
    save(ROOT/'data/manifests/asr_candidate_video_pilot.json', {k:v for k,v in result.items() if k!='records'} | {'packet':str(OUT)})
    print('COMPLETE', OUT, 'HUMAN REFERENCES', result['metrics']['verified_count'], '/3', flush=True)


if __name__ == '__main__':
    main()
