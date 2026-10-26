"""One post-selection control on3 frozen inputs; never train, score humans or change active weights."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'ai-core'),str(ROOT/'inference-service'),str(ROOT/'dist/kaggle/kernel-minigpt-news')]
from transcribe_pretrained_drafts import sha,save

BASE = Path('D:/data_training_ai/minigpt_real_video_20261015/asr_candidate_comparison_3_20261019')
OUT = Path('D:/data_training_ai/minigpt_news/aligned_candidate_video_control_3_v1')


def main():
    import torch
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import load_checkpoint
    from app.registry import registry
    from app import schemas,services

    verified = json.loads((ROOT/'docs/T1.6_aligned_training_metrics.json').read_text(encoding='utf-8'))
    assert verified['status']=='TRAINED_CANDIDATE_VERIFIED_NOT_DEPLOYED'
    checkpoint = Path(verified['candidate'])
    assert sha(checkpoint)==verified['candidate_sha256']
    control_file,paired_file = BASE/'confirmed_draft_minigpt.json',BASE/'comparison.json'
    active = ROOT/'ai-core/checkpoints/minigpt/best.pt'
    protected = {p:sha(p) for p in (control_file,paired_file,active)}
    old = json.loads(control_file.read_text(encoding='utf-8'))
    paired = json.loads(paired_file.read_text(encoding='utf-8'))
    assert protected[active]==old['checkpoint_sha256']==verified['active_sha256']
    assert sha(ROOT/'inference-service/app/services.py')==old['services_sha256']
    assert len(old['records'])==len(paired['records'])==3
    torch.set_num_threads(2)
    torch.manual_seed(1337)
    saved = load_checkpoint(str(checkpoint))
    model = build_model('minigpt',ModelConfig(**saved['config'])).float().eval()
    model.load_state_dict(saved['state_dict'],strict=True)
    registry.models['minigpt'],registry.device = model,'cpu'
    registry.minigpt_metadata = saved['metadata']
    registry.tokenizer = registry._rebuild_tokenizer(saved['bpe_vocab'])
    del saved
    OUT.mkdir(exist_ok=False)
    by_id = {r['sample_id']:r for r in paired['records']}
    records,text = [],['FROZEN3-VIDEO CONTROL, POST-VALIDATION SELECTION. No new human ratings.\n']
    with torch.inference_mode():
        for before in old['records']:
            sid = before['sample_id']
            assert before['user_content_confirmed']
            real = by_id[sid]
            assert before['candidate_asr_summary']==real['candidate']['summary']
            for kind,source,previous in (
                ('user_confirmed_draft',before['draft_text'],before['summary_from_confirmed_draft']),
                ('existing_candidate_asr_transcript',real['candidate']['asr']['full_transcript'],real['candidate']['summary'])):
                output = services._real_summarize(schemas.CompletionRequest(prompt=source,temperature=0,max_tokens=96))
                assert output.strip()
                item = {'sample_id':sid,'kind':kind,'source':source,'old_minigpt_summary':previous,
                        'new_minigpt_summary':output,'prior_user_judgment_old_candidate_asr_summary':before['candidate_summary_user_judgment'],
                        'new_human_quality_score':None}
                records.append(item)
                text.append(f"{sid} / {kind}\nSOURCE: {source}\nOLD: {previous}\nNEW: {output}\n")
                print('CONTROL',sid,kind,output,flush=True)
    assert len(records)==6 and all(sha(p)==v for p,v in protected.items())
    report = {'status':'POST_SELECTION_CONTROL_COMPLETE_NOT_HUMAN_SCORED',
              'candidate_sha256':verified['candidate_sha256'],'active_sha256':protected[active],
              'input_hashes':{str(p):v for p,v in protected.items()},'services_sha256':old['services_sha256'],
              'device':'cpu','dtype':'float32','torch':torch.__version__,'temperature':0,'max_tokens':96,
              'policy':'Exact existing3 input texts, no new ASR run/external model call, no tuning/selection on these clips',
              'records':records}
    save(OUT/'control.json',report)
    (OUT/'review.txt').write_text('\n'.join(text),encoding='utf-8')
    save(ROOT/'data/manifests/minigpt_aligned_video_control.json',
         {k:v for k,v in report.items() if k!='records'} | {'directory':str(OUT),'nonempty_outputs':6})


if __name__=='__main__':
    main()
