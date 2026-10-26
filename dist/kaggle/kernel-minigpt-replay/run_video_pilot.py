"""Fixed post-selection diagnostic: three clips, three inputs, two own MiniGPTs."""
import html
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'ai-core'),str(ROOT/'inference-service'),str(ROOT/'dist/kaggle/kernel-minigpt-news')]
from transcribe_pretrained_drafts import sha,save

BASE = Path('D:/data_training_ai/minigpt_real_video_20261015')
PAIRED = BASE/'asr_candidate_comparison_3_20261019'
OUT = Path('D:/data_training_ai/minigpt_news/mixed_replay_video_pilot_3_v1')
LABELS = {'user_confirmed_draft':'Bản nháp đã được xác nhận nội dung',
          'active_asr':'Transcript ASR đang dùng', 'candidate_asr':'Transcript ASR candidate (chưa deploy)'}


def review(records, videos):
    esc = html.escape
    cards = []
    for row in videos:
        sid = row['sample_id']
        sections = []
        for item in (r for r in records if r['sample_id']==sid):
            sections.append(f'<section><h3>{LABELS[item["kind"]]}</h3><details><summary>Xem nguyên văn đầu vào</summary>'
                            f'<p>{esc(item["source"])}</p></details><div class="pair">'
                            f'<div><h4>MiniGPT đang dùng</h4><p>{esc(item["active_summary"])}</p></div>'
                            f'<div><h4>MiniGPT mixed step300</h4><p>{esc(item["candidate_summary"])}</p></div></div></section>')
        cards.append(f'<article data-id="{esc(sid,quote=True)}"><h2>{esc(sid)} — {esc(row["title"])}</h2>'
                     f'<video controls preload="metadata" src="video/{esc(sid,quote=True)}.mp4"></video>'+''.join(sections)+'</article>')
    return ('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>MiniGPT mixed / active — 3 video chẩn đoán</title><style>'
            '*{box-sizing:border-box}body{font:16px system-ui;max-width:1200px;margin:auto;padding:24px;background:#fafafa;color:#222}'
            'article{background:white;border:1px solid #ccc;padding:20px;margin:24px 0}p{line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere}'
            'video{width:100%;max-height:400px}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}'
            'section{border-top:1px solid #ddd;padding:12px 0}details{margin:8px 0}h2{overflow-wrap:anywhere}'
            '@media(max-width:720px){body{padding:12px}article{padding:14px}.pair{grid-template-columns:1fr}}</style>'
            '<h1>MiniGPT đang dùng / mixed candidate</h1><p>3 clip đã từng xem: chỉ chẩn đoán, không phải test độc lập hoặc điểm chất lượng mới. '
            'Cùng đầu vào, CPU FP32, temperature=0/max_tokens=96. Cả hai cột đều chạy mới; không đổi model phục vụ. '
            'ASR được giữ đúng transcript đã lưu, không chạy lại hoặc sửa lời. Không tự chấm điểm thay người.</p>'+''.join(cards)+'</html>')


def main():
    import torch
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import load_checkpoint
    from app import schemas,services
    from app.registry import registry

    verified = json.loads((ROOT/'docs/T1.6_mixed_replay_metrics.json').read_text(encoding='utf-8'))
    assert verified['status']=='TRAIN_EVAL_VERIFIED_GUARD_PASSED_NOT_DEPLOYED'
    assert verified['selected_round']['step']==300 and verified['selected_round']['eligible']
    checkpoint = Path(verified['candidate'])
    active = ROOT/'ai-core/checkpoints/minigpt/best.pt'
    assert sha(checkpoint)==verified['candidate_sha256'] and sha(active)==verified['active_sha256']
    sources = [PAIRED/'confirmed_draft_minigpt.json',PAIRED/'comparison.json',
               BASE/'evaluation/samples.json',BASE/'asr_ground_truth_30/references.csv',
               ROOT/'inference-service/app/services.py',active,checkpoint]
    sources += sorted((BASE/'evaluation').glob('ratings_rater_*.csv'))
    protected = {p:sha(p) for p in sources}
    old,paired = [json.loads(p.read_text(encoding='utf-8')) for p in sources[:2]]
    assert old['checkpoint_sha256']==paired['checkpoints']['minigpt']==verified['active_sha256']
    assert old['services_sha256']==paired['services_sha256']==protected[ROOT/'inference-service/app/services.py']
    ids = ['sample_01','sample_10','sample_28']
    assert [r['sample_id'] for r in old['records']]==[r['sample_id'] for r in paired['records']]==ids
    by_id = {r['sample_id']:r for r in paired['records']}
    records = []
    for before in old['records']:
        assert before['user_content_confirmed']
        sid, real = before['sample_id'], by_id[before['sample_id']]
        for kind,source,cached in (
                ('user_confirmed_draft',before['draft_text'],before['summary_from_confirmed_draft']),
                ('active_asr',real['baseline']['asr']['full_transcript'],real['baseline']['summary']),
                ('candidate_asr',real['candidate']['asr']['full_transcript'],real['candidate']['summary'])):
            records.append({'sample_id':sid,'kind':kind,'source':source,'cached_active_summary':cached,
                            'active_summary':None,'candidate_summary':None,'new_human_quality_score':None})
    assert len(records)==9 and all(r['source'].strip() for r in records)
    OUT.mkdir(exist_ok=False)
    torch.set_num_threads(2)
    started = time.monotonic()
    for variant,path in (('active',active),('candidate',checkpoint)):
        torch.manual_seed(1337)
        saved = load_checkpoint(str(path))
        model = build_model('minigpt',ModelConfig(**saved['config'])).float().eval()
        model.load_state_dict(saved['state_dict'],strict=True)
        registry.models['minigpt'],registry.device = model,'cpu'
        registry.minigpt_metadata = saved['metadata']
        registry.tokenizer = registry._rebuild_tokenizer(saved['bpe_vocab'])
        del saved
        with torch.inference_mode():
            for item in records:
                output = services._real_summarize(schemas.CompletionRequest(prompt=item['source'],temperature=0,max_tokens=96))
                assert output.strip()
                item[variant+'_summary'] = output
                if variant=='active':
                    assert output==item['cached_active_summary'], 'active production helper/cache parity changed'
                print('PILOT',variant,item['sample_id'],item['kind'],output,flush=True)
        save(OUT/'progress.json',{'variant_completed':variant,'records':records})
    (OUT/'video').mkdir()
    for sid in ids:
        src = BASE/f'evaluation/video/{sid}.mp4'
        dest = OUT/f'video/{sid}.mp4'
        protected[src] = sha(src)
        shutil.copy2(src,dest)
        assert sha(dest)==protected[src]
    assert all(sha(p)==value for p,value in protected.items())
    report = {'status':'PAIRED_PILOT_COMPLETE_HUMAN_QUALITY_NOT_SCORED','sample_ids':ids,
              'candidate_sha256':verified['candidate_sha256'],'active_sha256':verified['active_sha256'],
              'asr_checkpoint_provenance':paired['checkpoints'],'device':'cpu','dtype':'float32','torch':torch.__version__,
              'temperature':0,'max_tokens':96,'elapsed_seconds':time.monotonic()-started,
              'new_asr_run':False,'production_weights_changed':False,'new_human_quality_score':None,
              'historical_shared_mean':1.6,'active_cache_parity_cases':9,'nonempty_generations':18,
              'policy':'Three previously inspected clips: diagnostic only, no training/tuning/checkpoint selection/deployment',
              'protected_hashes':{str(p):value for p,value in protected.items()},'records':records}
    save(OUT/'comparison.json',report)
    (OUT/'review.html').write_text(review(records,paired['records']),encoding='utf-8')
    text = [f"{r['sample_id']} / {r['kind']}\nSOURCE: {r['source']}\nACTIVE: {r['active_summary']}\nMIXED: {r['candidate_summary']}\n" for r in records]
    (OUT/'review.txt').write_text('\n'.join(text),encoding='utf-8')
    save(ROOT/'data/manifests/minigpt_mixed_video_pilot.json',
         {k:v for k,v in report.items() if k!='records'} | {'directory':str(OUT),'comparison_sha256':sha(OUT/'comparison.json'),
         'script_sha256':sha(Path(__file__)),'review_sha256':sha(OUT/'review.html')})
    print('PILOT VERIFIED:18 fresh generations; active cache parity9/9; protected hashes unchanged.',flush=True)


if __name__=='__main__':
    main()
