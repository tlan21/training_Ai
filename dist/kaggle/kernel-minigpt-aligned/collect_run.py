"""Collect this authorized candidate and verify validation evidence; never promote weights."""
import json
import sys
import time
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'ai-core'),str(ROOT/'dist/kaggle/kernel-minigpt-news')]
from ai_core.data.manifest import file_checksum
from ai_core.training.checkpoint import load_checkpoint
from transcribe_pretrained_drafts import sha,save

KERNEL = 'traininghighlight/ai-core-minigpt-aligned-v2'
DATA = Path('D:/data_training_ai/minigpt_news/aligned_training_upload_20261019')
OUT = Path('D:/data_training_ai/minigpt_news/aligned_output_v1')


def main():
    OUT.mkdir(exist_ok=False)
    active = ROOT/'ai-core/checkpoints/minigpt/best.pt'
    protected = sha(active)
    assert protected=='cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac'
    api = KaggleApi()
    api.authenticate()
    while True:
        response = api.kernels_status(KERNEL)
        status = response.status.name
        save(OUT/'watch_status.json',{'kernel':KERNEL,'version':1,'status':status,'checked_at_unix':time.time()})
        print(time.strftime('%Y-%m-%d %H:%M:%S'),status,flush=True)
        if status in ('COMPLETE','ERROR','CANCEL_ACKNOWLEDGED'):
            break
        time.sleep(30)
    token = None
    while True:
        _,token = api.kernels_output(KERNEL+'/1',path=str(OUT),force=True,quiet=True,page_token=token)
        if not token:
            break
    if status!='COMPLETE':
        raise SystemExit('Candidate did not complete; inspect downloaded log; no deployment')
    assert sha(active)==protected
    verify()


def verify():
    active = ROOT/'ai-core/checkpoints/minigpt/best.pt'
    protected = sha(active)
    assert protected=='cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac'
    watch = json.loads((OUT/'watch_status.json').read_text(encoding='utf-8'))
    assert watch['kernel']==KERNEL and watch['version']==1 and watch['status']=='COMPLETE'
    files = {name:list(OUT.rglob(name)) for name in ('training_result.json','aligned_baseline.json','aligned_runtime.json','validation.jsonl')}
    assert all(len(paths)==1 for paths in files.values()),'missing/ambiguous job evidence'
    result = json.loads(files['training_result.json'][0].read_text(encoding='utf-8'))
    baseline = json.loads(files['aligned_baseline.json'][0].read_text(encoding='utf-8'))
    runtime = json.loads(files['aligned_runtime.json'][0].read_text(encoding='utf-8'))
    validation = [json.loads(s) for s in files['validation.jsonl'][0].read_text(encoding='utf-8').splitlines() if s.strip()]
    expected = json.loads((DATA/'news_manifest.json').read_text(encoding='utf-8'))
    assert result['dataset']['splits']==expected['splits']
    assert result['dataset']['human_audit_sha256']==sha(DATA/'human_audit.csv')
    assert baseline['init_sha256']==protected
    assert baseline['data_manifest_sha256']==sha(DATA/'news_manifest.json')
    assert result['seed']==runtime['seed']==1337 and baseline['n_val']==64
    assert runtime['completed'] and runtime['train_8gib_pass']
    assert runtime['peak_allocated_gib']<=8 and runtime['peak_reserved_gib']<=8
    stages = {s['stage']:s for s in result['stages']}
    assert {s:v['train']['step'] for s,v in stages.items()}=={'clean':240,'asr':60}
    assert len(validation)==5 and [v['stage'] for v in validation]==['clean']*4+['asr']
    for entry in validation:
        measured = (entry['formats']['sum_clean']['rouge_l']+entry['formats']['sum_asr']['rouge_l'])/2
        assert abs(entry['selection_score']-measured)<1e-9
    chosen = max(result['stages'],key=lambda x:x['metric'])
    assert result['selected_stage']==chosen['stage'] and result['selected_step']==chosen['best_step']
    assert abs(result['validation_metric']-chosen['metric'])<1e-9
    matching = [v for v in validation if v['stage']==chosen['stage'] and abs(v['selection_score']-chosen['metric'])<1e-9]
    assert matching
    candidate = files['training_result.json'][0].parent/'minigpt/best.pt'
    assert file_checksum(str(candidate))==result['checkpoint_sha1']
    checkpoint = load_checkpoint(str(candidate))
    assert checkpoint['metrics']['step']==result['selected_step']
    assert abs(checkpoint['metrics']['rouge_l']-result['validation_metric'])<1e-9
    assert {k:checkpoint['config'][k] for k in ('d_model','n_layers','n_heads','vocab_size','context_len')}=={
        'd_model':384,'n_layers':6,'n_heads':6,'vocab_size':8192,'context_len':1024}
    assert checkpoint['metadata']['corpus']['human_audit_sha256']==sha(DATA/'human_audit.csv')
    assert sha(active)==protected
    report = {'status':'TRAINED_CANDIDATE_VERIFIED_NOT_DEPLOYED','kernel':KERNEL,'kernel_version':1,
              'dataset':'traininghighlight/minigpt-aligned-summary-v2','seed':1337,'n_train':956,'n_val':64,
              'candidate':str(candidate),'candidate_sha256':sha(candidate),'active_sha256':protected,
              'selected_stage':result['selected_stage'],'selected_step':result['selected_step'],
              'baseline_same_gpu_selection':baseline['selection_score'],
              'candidate_selection':result['validation_metric'],
              'selection_delta':result['validation_metric']-baseline['selection_score'],
              'baseline_metrics':baseline['metrics'],'candidate_metrics':matching[0]['formats'],
              'runtime':runtime,'elapsed_hours':result['elapsed_hours'],
              'human_model_quality':'NOT RE-SCORED - label-support confirmation is not a model quality rating',
              'frozen_test_evaluation_run':False,'production_weights_changed':False,
              'artifact_hashes':{k:sha(paths[0]) for k,paths in files.items()}}
    save(OUT/'verification.json',report)
    save(ROOT/'docs/T1.6_aligned_training_metrics.json',report)
    manifest = json.loads((ROOT/'data/manifests/minigpt_aligned_training.json').read_text(encoding='utf-8'))
    save(ROOT/'data/manifests/minigpt_aligned_training.json',{**manifest,**report})
    print('VERIFIED',json.dumps({k:report[k] for k in ('selected_stage','selected_step','baseline_same_gpu_selection','candidate_selection','selection_delta','candidate_sha256')}),flush=True)


if __name__=='__main__':
    main()
