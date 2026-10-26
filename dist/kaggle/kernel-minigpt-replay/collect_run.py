"""Download the fixed replay experiment and verify its guard; never deploy weights."""
import json
import math
import sys
import time
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'ai-core'),str(ROOT/'dist/kaggle/kernel-minigpt-news')]
from ai_core.data.manifest import file_checksum
from ai_core.scripts.finetune_news_summary import replay_regressions
from ai_core.training.checkpoint import load_checkpoint
from transcribe_pretrained_drafts import sha,save

KERNEL = 'traininghighlight/ai-core-minigpt-replay-v1'
DATA = Path('D:/data_training_ai/minigpt_news/mixed_replay_upload_20261019')
OUT = Path('D:/data_training_ai/minigpt_news/mixed_replay_output_v1')
ACTIVE_SHA = 'cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac'


def verify():
    assert sha(ROOT/'ai-core/checkpoints/minigpt/best.pt') == ACTIVE_SHA
    watch = json.loads((OUT/'watch_status.json').read_text(encoding='utf-8'))
    assert watch['kernel']==KERNEL and watch['version']==1 and watch['status']=='COMPLETE'
    names = ('training_result.json','replay_baseline.json','replay_runtime.json',
             'validation.jsonl','validation_predictions.jsonl')
    files = {name:list(OUT.rglob(name)) for name in names}
    assert all(len(paths)==1 for paths in files.values()), 'missing/ambiguous evidence'
    def read(name):
        return json.loads(files[name][0].read_text(encoding='utf-8'))
    result, baseline, runtime = (read(n) for n in names[:3])
    validation, predictions = ([json.loads(s) for s in files[n][0].read_text(encoding='utf-8').splitlines() if s.strip()]
                               for n in names[3:])
    expected = json.loads((DATA/'news_manifest.json').read_text(encoding='utf-8'))
    assert result['dataset'] == expected
    assert expected['human_audit_sha256']==sha(DATA/'human_audit.csv')
    assert baseline['data_manifest_sha256']==sha(DATA/'news_manifest.json')
    assert baseline['init_sha256']==sha(DATA/'pretrain.pt')==ACTIVE_SHA
    assert baseline['n_val']==64 and baseline['eval_precision']=='fp16_autocast'
    assert result['recipe']=='mixed-replay-1to1-v1' and result['seed']==runtime['seed']==1337
    assert runtime['completed'] and runtime['train_8gib_pass']
    assert runtime['peak_allocated_gib']<=8 and runtime['peak_reserved_gib']<=8
    assert len(result['stages'])==1 and result['stages'][0]['stage']=='mixed'
    assert result['stages'][0]['train']['step']==300
    assert len(validation)==len(predictions)==5
    assert [v['step'] for v in validation]==[60,120,180,240,300]
    assert result['selection_guard']['baseline_metrics']==baseline['metrics']
    assert result['selection_guard']['baseline_sha256']==sha(files['replay_baseline.json'][0])
    for entry, raw in zip(validation,predictions):
        assert entry['stage']==raw['stage']=='mixed'
        measured = (entry['formats']['sum_clean']['rouge_l']+entry['formats']['sum_asr']['rouge_l'])/2
        assert math.isfinite(measured) and abs(entry['selection_score']-measured)<1e-12
        failed = replay_regressions(entry['formats'],baseline['metrics'])
        assert entry['eligible']==(not failed) and entry['regressions']==failed
        for name, metrics in entry['formats'].items():
            values = raw['predictions'][name]
            assert [v['id'] for v in values]==expected['validation_ids']
            for key, value in metrics.items():
                assert abs(sum(v[key] for v in values)/64-value)<1e-12
    run = files['training_result.json'][0].parent
    last = load_checkpoint(str(run/'mixed/minigpt/last.pt'))
    assert last['metrics']['step']==300 and last['metrics']['seed']==1337
    assert last['metadata']['recipe']=='mixed-replay-1to1-v1'
    assert last['train_config']['batch_size']==8 and last['train_config']['grad_accum']==8
    assert last['train_config']['max_steps']==300 and last['train_config']['eval_every']==60
    assert last['train_config']['lr']==1e-4
    assert {k:last['config'][k] for k in ('d_model','n_layers','n_heads','vocab_size','context_len')}=={
        'd_model':384,'n_layers':6,'n_heads':6,'vocab_size':8192,'context_len':1024}
    eligible = [v for v in validation if v['eligible']]
    chosen = max(eligible,key=lambda v:v['selection_score'],default=None)
    candidate = run/'minigpt/best.pt'
    if chosen:
        assert result['status']=='CANDIDATE_ONLY_HELDOUT_AND_HUMAN_EVALUATION_PENDING'
        assert result['selected_stage']=='mixed' and result['selected_step']==chosen['step']
        assert abs(result['validation_metric']-chosen['selection_score'])<1e-12
        assert file_checksum(str(candidate))==result['checkpoint_sha1']
        checkpoint = load_checkpoint(str(candidate))
        assert checkpoint['metrics']['step']==chosen['step']
        assert checkpoint['metrics']['rouge_l']==result['validation_metric']
    else:
        assert result['status']=='NO_CANDIDATE_PASSED_NON_REGRESSION_GUARD'
        assert result['selected_stage'] is result['selected_step'] is result['validation_metric'] is result['checkpoint_sha1'] is None
        assert not candidate.exists(), 'rejected model must not be exported as serving candidate'
    logs = list(OUT.glob('*.log'))
    assert len(logs)==1
    try:
        log = logs[0].read_text(encoding='utf-8')
    except UnicodeDecodeError:
        log = logs[0].read_text(encoding='cp1252')
    log = ''.join(entry['data'] for entry in json.loads(log))
    for marker in ('SANITY gradient <1e-4 PASS','SANITY AdamW <1e-6 PASS',
                   'SANITY BPE10000/10000 PASS','SANITY MiniGPT toy1batch loss<0.05 PASS'):
        assert marker in log
    report = {'status':'TRAIN_EVAL_VERIFIED_GUARD_PASSED_NOT_DEPLOYED' if chosen else 'TRAIN_EVAL_VERIFIED_NO_ELIGIBLE_CANDIDATE',
              'kernel':KERNEL,'kernel_version':1,'dataset':'traininghighlight/minigpt-mixed-replay-v1',
              'seed':1337,'n_train':956,'n_val':64,'recipe':result['recipe'],
              'baseline_metrics':baseline['metrics'],'baseline_selection':baseline['selection_score'],
              'eligible_rounds':len(eligible),'validation_rounds':validation,
              'selected_round':chosen,'diagnostic_max_mean_round':max(validation,key=lambda v:v['selection_score']),
              'candidate':str(candidate) if chosen else None,'candidate_sha256':sha(candidate) if chosen else None,
              'diagnostic_last_checkpoint':str(run/'mixed/minigpt/last.pt'),
              'diagnostic_last_sha256':sha(run/'mixed/minigpt/last.pt'),
              'active_sha256':ACTIVE_SHA,'runtime':runtime,'elapsed_hours':result['elapsed_hours'],
              'remote_sanity_checks_passed':4,'production_weights_changed':False,'frozen_test_evaluation_run':False,
              'human_model_quality':'NOT RE-SCORED; historical shared mean1.6/5 unchanged',
              'artifact_hashes':{name:sha(paths[0]) for name,paths in files.items()}}
    assert sha(ROOT/'ai-core/checkpoints/minigpt/best.pt')==ACTIVE_SHA
    save(OUT/'verification.json',report)
    save(ROOT/'docs/T1.6_mixed_replay_metrics.json',report)
    p = ROOT/'data/manifests/minigpt_mixed_replay.json'
    save(p,{**json.loads(p.read_text(encoding='utf-8')),**report})
    print('VERIFIED',report['status'],'eligible rounds',len(eligible),'selected',result['selected_step'],flush=True)


def main():
    OUT.mkdir(exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    while True:
        status = api.kernels_status(KERNEL).status.name
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
        raise SystemExit('Training did not complete; inspect log; no deployment')
    verify()


if __name__=='__main__':
    main()
