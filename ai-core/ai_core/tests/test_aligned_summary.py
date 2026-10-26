import csv

import pytest
import torch

from ai_core.scripts.prepare_aligned_summary import check_human_audit, clean_label, pair_sha, screen_pair, has_sentence_ending
from ai_core.tokenizer import BPETokenizer


def article():
    return {'id': 'a'*64, 'title': 'City opens new school',
            'summary': '(TNO) City opens a new school for 20 children.',
            'body': 'City opens a new school for 20 children. Parents visit the school today.'}


def test_screen_preserves_complete_editorial_label_and_reproducible_asr():
    tok = BPETokenizer()
    a, reason = screen_pair(article(), tok)
    assert reason is None and a['summary'] == 'City opens a new school for 20 children.'
    assert a == screen_pair(article(), tok)[0]
    assert clean_label('(2026) A real date.') == '(2026) A real date.'
    assert clean_label('(TNO) A label.') == 'A label.'
    assert a['body'] == article()['body']


def test_word_screen_is_not_a_semantic_factuality_certificate():
    altered = {**article(), 'summary':'20 children visit the City school today.'}
    # All words occur, but the source only says that parents visit; human review is still needed.
    assert screen_pair(altered, BPETokenizer())[0] is not None


@pytest.mark.parametrize('ending', ['...', '…', '…)', '..."', '…”', '...)', '..'])
def test_screen_rejects_terminal_ellipsis_instead_of_certifying_a_teaser(ending):
    target = 'City opens a new school for 20 children'+ending
    assert not has_sentence_ending(target)
    assert screen_pair({**article(),'summary':target},BPETokenizer()) == (None,'incomplete_summary')


def test_internal_ellipsis_does_not_reject_an_otherwise_punctuated_ending():
    assert has_sentence_ending('City opens... a school today.')
    assert has_sentence_ending('City opens a school today!"')
    assert not has_sentence_ending('City opens a school today')


@pytest.mark.parametrize('changes,reason', [
    ({'summary': 'City opens a new school for 20 children'}, 'incomplete_summary'),
    ({'summary': 'City opens a new school for 30 children.'}, 'unsupported_numeric_span'),
    ({'summary': 'City opens a new school for 20 adults.'}, 'unsupported_target_word'),
    ({'summary': 'City opens a new school for 20 children. '*4}, 'target_over_budget'),
    ({'body': article()['body']+' More information.'*40}, 'clean_source_over_budget'),
])
def test_screen_rejects_unsupported_or_truncated_pairs(changes, reason):
    assert screen_pair({**article(), **changes}, BPETokenizer()) == (None, reason)


def test_audit_gate_requires_real_annotations_and_exact_pair_identity(tmp_path):
    row = screen_pair(article(), BPETokenizer())[0]
    expected = {'split': 'train', 'id': row['id'], 'pair_sha256': pair_sha(row)}
    manifest = {'audit_sample': [expected]}
    path = tmp_path/'audit.csv'

    def write(rows):
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=[*expected, 'reviewer','verdict'])
            writer.writeheader()
            writer.writerows(rows)

    for changes in ({}, {'reviewer':'', 'verdict':'supported'}, {'reviewer':'Test human', 'verdict':'reject'},
                    {'reviewer':'Test human', 'verdict':'supported', 'pair_sha256':'stale'}):
        write([{**expected, **changes}])
        with pytest.raises(ValueError):
            check_human_audit(path, manifest, {'train':[row]})
    # Synthetic fixture only; never written to the real human audit packet.
    supported = {**expected, 'reviewer':'Test human', 'verdict':'supported'}
    write([supported])
    check_human_audit(path, manifest, {'train':[row]})
    with pytest.raises(ValueError):
        check_human_audit(path, manifest, {'train':[{**row, 'summary':'Changed label.'}]})
    write([supported, supported])
    with pytest.raises(ValueError):
        check_human_audit(path, manifest, {'train':[row]})


def test_aligned_training_uses_same_source_without_sapo_and_preserves_targets():
    from ai_core.scripts.finetune_news_summary import encoded_dataset
    from ai_core.training.datasets.summary_dataset import summary_prompt_ids

    tok = BPETokenizer()
    row = screen_pair(article(), tok)[0]
    row['source_asr'] = '  '+row['source_asr']+' \n'
    for noisy in (False, True):
        items = encoded_dataset([row], tok, noisy, aligned=True)
        assert len(items) == 4
        for fmt, (x,y) in zip(('title','title','sum','cap'), items):
            source = (row['source_asr'] if noisy else row['body']).strip()
            prompt = summary_prompt_ids(source, tok, fmt, 512, 96)
            target = row['summary'] if fmt=='sum' else row['title']
            assert x[:len(prompt)].tolist() == prompt
            assert y[:len(prompt)-1].eq(-100).all()
            assert y[len(prompt)-1:].tolist() == tok.encode(target)+[tok.special_tokens['<eos>']]


def test_sum_selection_ignores_better_titles_and_pairs_clean_noisy_ids():
    from ai_core.scripts.finetune_news_summary import aligned_validation
    from ai_core.training.datasets.summary_dataset import CONTROL_TOKENS

    tok = BPETokenizer()
    row = screen_pair(article(), tok)[0]

    class Output:
        def __init__(self, sum_correct):
            self.sum_correct = sum_correct
            self.sources = []

        def eval(self):
            return self

        def generate(self, prompt, budget, temperature, eos_id):
            text = tok.decode(prompt[0,:-1].tolist())
            self.sources.append(text)
            if text.startswith(CONTROL_TOKENS['sum']):
                pred = row['summary'] if self.sum_correct else 'Wrong unrelated facts.'
            else:
                pred = 'Wrong headline.' if self.sum_correct else row['title']
            return torch.cat([prompt, torch.tensor([tok.encode(pred)+[eos_id]])], dim=1)

    strong_sum, strong_title = Output(True), Output(False)
    a, ma, pa = aligned_validation(strong_sum, [row], tok, torch.device('cpu'))
    b, mb, pb = aligned_validation(strong_title, [row], tok, torch.device('cpu'))
    assert a == 1 and a > b
    assert ma['title_clean']['rouge_l'] < mb['title_clean']['rouge_l'] == 1
    assert [r['id'] for r in pa['sum_clean']] == [r['id'] for r in pa['sum_asr']]
    assert strong_sum.sources[0] == '<sum> '+row['body']
    assert strong_sum.sources[1] == '<sum> '+row['source_asr'].strip()
    assert all(not v['cap_hit'] and v['eos_stop'] for values in pa.values() for v in values)


def test_bundle_cannot_start_training_with_insufficient_validation(tmp_path):
    from ai_core.scripts.finetune_news_summary import validate_aligned_bundle

    with pytest.raises(ValueError, match='need64'):
        validate_aligned_bundle(tmp_path, {'validation_ids':[]}, [], [])


def test_reserve_preserves_frozen_ids_and_stops_at_declared_validation_count(monkeypatch):
    from ai_core.scripts import prepare_aligned_summary as prep

    rows = [{'title':article()['title'], 'summary':article()['summary'],
             'content':article()['body']+' a'*60+f' {i}.'} for i in range(5)]
    rows[1]['summary'] = 'City opens a new school for 31 children.'
    frozen = prep.record(rows[0])['id']
    monkeypatch.setattr(prep, 'VAL_COUNT', 2)
    monkeypatch.setattr(prep, 'reserve_split', lambda _: 'val')
    parts = {'train':[], 'val':[]}
    counts = prep.extend_pairs(rows, parts, {frozen}, BPETokenizer())
    assert counts['duplicate_or_frozen_id'] == 1
    assert counts['unsupported_numeric_span'] == 1
    assert counts['accepted_val'] == 2 and counts['raw_rows_scanned'] == 4
    assert not parts['train'] and frozen not in {r['id'] for r in parts['val']}


def test_evaluator_reports_repetition_and_budget_hit_without_calling_it_factuality():
    from ai_core.scripts.finetune_news_summary import evaluate

    tok = BPETokenizer()
    row = screen_pair(article(), tok)[0]

    class Repeating:
        def eval(self):
            return self

        def generate(self, prompt, budget, temperature, eos_id):
            ids = tok.encode('a '*48)
            assert len(ids) == budget == 96
            return torch.cat([prompt, torch.tensor([ids])], dim=1)

    result = evaluate(Repeating(), [row], tok, torch.device('cpu'), fmt='sum', aligned=True)[0]
    assert result['cap_hit'] and not result['eos_stop']
    assert result['repeated_trigram_fraction'] > .9


def test_small_dataset_uses_epoch_budget_and_legacy_experiment_stays_reproducible():
    from ai_core.scripts.finetune_news_summary import training_schedule

    stages, every = training_schedule(100,8,8,True)
    assert every == 7 and stages == (('clean',28,False),('asr',7,True))
    legacy, every = training_schedule(100,8,8,False)
    assert every == 1000 and legacy == (('clean',16000,False),('asr',4000,True))
    with pytest.raises(ValueError, match='empty'):
        training_schedule(0,8,8,True)


def test_replay_microbatches_are_balanced_complete_and_seeded_across_epochs():
    from ai_core.scripts.finetune_news_summary import ReplayBatchSampler, training_schedule

    a, b = ReplayBatchSampler(11,8,1337), ReplayBatchSampler(11,8,1337)
    first = list(a)
    assert first == list(b) and len(first) == len(a) == 3
    assert sorted(i for batch in first for i in batch) == list(range(22))
    assert all(sum(i < 11 for i in batch) == len(batch)//2 for batch in first)
    second = list(a)
    assert second == list(b) and second != first
    assert training_schedule(956,8,8,True,True) == ((('mixed',300,None),),60)
    with pytest.raises(ValueError, match='confirmed aligned'):
        training_schedule(956,8,8,False,True)
    for n, batch in ((0,8),(1,1),(3,7)):
        with pytest.raises(ValueError, match='even batch'):
            ReplayBatchSampler(n,batch,1337)


def replay_metrics():
    return {name:{'rouge_l':.2,'eos_stop':.8,'cap_hit':.2,'repeated_trigram_fraction':.1}
            for name in ('sum_clean','sum_asr')}


@pytest.mark.parametrize('condition', ['sum_clean','sum_asr'])
@pytest.mark.parametrize('key,bad', [('rouge_l',.19),('eos_stop',.79),('cap_hit',.21),
                                    ('repeated_trigram_fraction',.11),('rouge_l',float('nan'))])
def test_replay_guard_rejects_each_condition_even_if_paired_mean_improves(condition,key,bad):
    from ai_core.scripts.finetune_news_summary import replay_regressions, select_candidate

    baseline, candidate = replay_metrics(), replay_metrics()
    other = 'sum_clean' if condition=='sum_asr' else 'sum_asr'
    candidate[other]['rouge_l'] = .9
    candidate[condition][key] = bad
    assert replay_regressions(candidate,baseline) == [f'{condition}.{key}']
    assert select_candidate([{'metric':-1.}],guarded=True) is None
    assert select_candidate([{'metric':.25},{'metric':-1.}],guarded=True) == {'metric':.25}


def test_replay_guard_accepts_equality_or_joint_improvement_and_refuses_bad_baseline():
    from ai_core.scripts.finetune_news_summary import replay_regressions

    baseline, candidate = replay_metrics(), replay_metrics()
    assert not replay_regressions(candidate,baseline)
    for group in candidate.values():
        group.update(rouge_l=.3,eos_stop=.9,cap_hit=.1,repeated_trigram_fraction=.05)
    assert not replay_regressions(candidate,baseline)
    baseline['sum_asr']['rouge_l'] = float('nan')
    with pytest.raises(ValueError,match='invalid replay baseline'):
        replay_regressions(candidate,baseline)


def test_replay_entrypoint_exports_no_candidate_when_all_rounds_fail(tmp_path,monkeypatch):
    import hashlib
    import json
    import sys
    from ai_core.config import ModelConfig, TrainConfig
    from ai_core.data.manifest import file_checksum
    from ai_core.scripts import finetune_news_summary as run
    from ai_core.training.checkpoint import save_checkpoint

    tok = BPETokenizer()
    tok.save(str(tmp_path/'vocab.json'))
    model = torch.nn.Linear(1,1)
    model_cfg = ModelConfig(name='minigpt',vocab_size=tok.vocab_size)
    cfg = TrainConfig(model='minigpt',batch_size=8,grad_accum=8,metric_name='rouge_l')
    save_checkpoint(str(tmp_path/'init.pt'),model,model_cfg,{},None,{})
    manifest = {'protocol':run.PROTOCOL,'splits':{},'vocab_sha1':file_checksum(str(tmp_path/'vocab.json')),
                'selection':'fixture only'}
    for name,rows in (('train',[article()]),('val',[article()]*64)):
        p = tmp_path/f'news_{name}.json'
        p.write_text(json.dumps(rows),encoding='utf-8')
        manifest['splits'][name] = {'sha1':file_checksum(str(p))}
    path = tmp_path/'news_manifest.json'
    path.write_text(json.dumps(manifest),encoding='utf-8')
    baseline = {'init_sha256':hashlib.sha256((tmp_path/'init.pt').read_bytes()).hexdigest(),
                'data_manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'n_val':64,'eval_precision':'fp16_autocast','metrics':replay_metrics()}
    (tmp_path/'baseline.json').write_text(json.dumps(baseline),encoding='utf-8')
    rejected = replay_metrics()
    rejected['sum_asr']['rouge_l'] = .1
    monkeypatch.setattr(run,'validate_aligned_bundle',lambda *args:None)
    monkeypatch.setattr(run,'load_configs',lambda _: (model_cfg,cfg))
    monkeypatch.setattr(run,'build_model',lambda *args:model)
    monkeypatch.setattr(run,'encoded_dataset',lambda *args,**kwargs:[(torch.ones(1),torch.ones(1))])
    monkeypatch.setattr(run,'aligned_validation',lambda *args:(.15,rejected,{}))
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    monkeypatch.setattr(torch.cuda,'is_bf16_supported',lambda **kwargs:False)
    monkeypatch.setattr(torch.cuda,'get_device_name',lambda _: 'fixture')

    class RejectedTrainer:
        def __init__(self,model,loader,val,cfg,loss,**kwargs):
            self.metric = kwargs['compute_metric']

        def train(self):
            for _ in range(5):
                assert self.metric(model,None,torch.device('cpu')) == -1
            save_checkpoint(str(tmp_path/'out/mixed/minigpt/best.pt'),model,model_cfg,
                            {'rouge_l':-1.,'step':1},None,{})
            return {'step':5,'seed':1337}

    monkeypatch.setattr(run,'Trainer',RejectedTrainer)
    monkeypatch.setattr(sys,'argv',['train','--data',str(tmp_path),'--vocab',str(tmp_path/'vocab.json'),
                                  '--pretrain',str(tmp_path/'init.pt'),'--output',str(tmp_path/'out'),
                                  '--mixed-replay','--baseline',str(tmp_path/'baseline.json')])
    run.main()
    result = json.loads((tmp_path/'out/training_result.json').read_text(encoding='utf-8'))
    assert result['status']=='NO_CANDIDATE_PASSED_NON_REGRESSION_GUARD'
    assert result['selected_stage'] is result['selected_step'] is result['checkpoint_sha1'] is None
    assert not (tmp_path/'out/minigpt').exists()


def test_training_entrypoint_refuses_pending_audit_before_gpu_or_output(tmp_path,monkeypatch):
    import json
    import sys
    from ai_core.data.manifest import file_checksum
    from ai_core.scripts.finetune_news_summary import main
    from ai_core.scripts.prepare_aligned_summary import PROTOCOL

    row = screen_pair(article(), BPETokenizer())[0]
    train = [{**row,'id':'0'*64}]
    val = [{**row,'id':f'{i:064x}'} for i in range(1,65)]
    manifest = {'protocol':PROTOCOL, 'context':512, 'output_tokens':96, 'asr_cer':.1347,
                'validation_ids':[r['id'] for r in val], 'splits':{},
                'audit_sample':[{'split':'train','id':train[0]['id'],'pair_sha256':pair_sha(train[0])}]}
    for split,rows in (('train',train),('val',val)):
        path = tmp_path/f'news_{split}.json'
        path.write_text(json.dumps(rows),encoding='utf-8')
        manifest['splits'][split] = {'count':len(rows),'sha1':file_checksum(str(path))}
    (tmp_path/'news_manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    with (tmp_path/'human_audit.csv').open('w',encoding='utf-8',newline='') as target:
        writer = csv.DictWriter(target,fieldnames=['split','id','pair_sha256','reviewer','verdict'])
        writer.writeheader()
        writer.writerows(manifest['audit_sample'])
    out = tmp_path/'must-not-be-created'
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    monkeypatch.setattr(sys,'argv',['train','--data',str(tmp_path),'--vocab','unused','--pretrain','unused','--output',str(out)])
    with pytest.raises(ValueError,match='human audit pending'):
        main()
    assert not out.exists()
    train[0]['summary'] = train[0]['summary'].rstrip('.')+'...'
    from ai_core.scripts.finetune_news_summary import validate_aligned_bundle
    with pytest.raises(ValueError,match='1 summaries have invalid sentence endings'):
        validate_aligned_bundle(tmp_path,manifest,train,val)
