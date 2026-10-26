"""Audit existing MiniGPT on train/validation only; no tuning, training or deployment."""
import collections
import itertools
import json
import math
import re
import sys
from pathlib import Path

from transcribe_pretrained_drafts import ROOT, sha, save

sys.path[:0] = [str(ROOT/'ai-core'), str(ROOT/'inference-service')]
from ai_core.data.manifest import file_checksum
from ai_core.scripts.evaluate import rouge_l
from ai_core.training.datasets.summary_dataset import CONTROL_TOKENS, SummaryPairDataset, summary_prompt_ids

DATA = Path('D:/data_training_ai/minigpt_news/dataset')
OUT = Path('D:/data_training_ai/minigpt_news/pipeline_diagnostic_20261019')


def array_rows(path):
    """Read the pinned prepared JSON array without loading all288MB into memory."""
    decoder = json.JSONDecoder()
    with path.open(encoding='utf-8') as source:
        assert source.read(1) == '['
        buffer, value_expected, seen = '', True, False
        while True:
            buffer = buffer.lstrip()
            if not buffer:
                buffer = source.read(65536)
                if not buffer:
                    raise ValueError('unterminated JSON array')
                continue
            if buffer.startswith(']'):
                if value_expected and seen:
                    raise ValueError('trailing comma')
                return
            if not value_expected:
                if buffer[0] != ',':
                    raise ValueError('missing JSON array separator')
                buffer, value_expected = buffer[1:], True
                continue
            try:
                row, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                extra = source.read(65536)
                if not extra:
                    raise ValueError('incomplete JSON array record')
                buffer += extra
                continue
            assert isinstance(row, dict)
            yield row
            buffer, value_expected, seen = buffer[end:], False, True


def repeated_trigram_fraction(text):
    words = text.casefold().split()
    grams = list(zip(words, words[1:], words[2:]))
    return 1-len(set(grams))/len(grams) if grams else 0.


def source_profile(row, tok):
    prefix = tok.encode('<sum>')
    capacity = 512-96-1-len(prefix)
    ids = tok.encode(' '+row['body'])
    visible = tok.decode(ids[:capacity])
    target = row['summary']
    labels = tok.encode(target)
    prompt = prefix+ids[:capacity]+[tok.special_tokens['<eos>']]
    assert prompt == summary_prompt_ids(row['body'], tok, 'sum', 512, 96), 'real BPE prompt mismatch'
    words = lambda s: set(re.findall(r'\w+', s.casefold()))
    tw, full, vw = words(target), words(row['body']), words(visible)
    return {'source_tokens': len(ids), 'source_truncated': len(ids)>capacity,
            'target_tokens': len(labels), 'target_truncated': len(labels)>95,
            'target_word_overlap_full_body': len(tw & full)/max(1,len(tw)),
            'target_word_overlap_visible_prefix': len(tw & vw)/max(1,len(tw)),
            'target_has_parenthesized_prefix': bool(re.match(r'^\s*\([^)]{1,45}\)', target)),
            'target_contains_duplicate_trigrams': repeated_trigram_fraction(target)>0,
            'prompt_matches_training': True}


def main():
    import torch
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import load_checkpoint
    from ai_core.training.loss_fns import minigpt_loss
    from app import schemas, services
    from app.registry import registry

    torch.set_num_threads(2)
    torch.manual_seed(1337)
    ckpt = ROOT/'ai-core/checkpoints/minigpt/best.pt'
    protected = {ckpt: sha(ckpt)}
    assert protected[ckpt] == 'cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac'
    manifest = json.loads((DATA/'news_manifest.json').read_text(encoding='utf-8'))
    for split in ['train','val']:
        assert file_checksum(str(DATA/f'news_{split}.json')) == manifest['splits'][split]['sha1']
    val = json.loads((DATA/'news_val.json').read_text(encoding='utf-8'))
    assert len(val) == 4000
    # Fixed before looking at outputs; these validation rows were outside the original128 selection subset.
    chosen = [(i,r) for i,r in enumerate(val) if i>=128 and len(r['summary'].split())>=5][:8]
    assert len(chosen) == 8
    OUT.mkdir(exist_ok=False)
    saved = load_checkpoint(str(ckpt))
    model = build_model('minigpt', ModelConfig(**saved['config'])).eval()
    model.load_state_dict(saved['state_dict'], strict=True)
    registry.models['minigpt'] = model
    registry.device = 'cpu'
    registry.minigpt_metadata = saved['metadata']
    tok = registry._rebuild_tokenizer(saved['bpe_vocab'])
    registry.tokenizer = tok
    metadata = saved['metadata']
    del saved
    audit, counts, train_ids = [], collections.Counter(), set()
    for i,row in enumerate(array_rows(DATA/'news_train.json')):
        counts['train_articles'] += 1
        train_ids.add(row['id'])
        eligible = len(row['summary'].split())>=5
        counts['sum_eligible'] += eligible
        if i<256 and eligible:
            audit.append(source_profile(row,tok))
    assert counts['train_articles']==len(train_ids)==76000
    assert not train_ids & {r['id'] for r in val}
    counts['title_or_cap_target_instances'] = 3*counts['train_articles']
    counts['sum_target_instances'] = counts['sum_eligible']
    counts['sum_training_fraction'] = counts['sum_eligible']/(counts['sum_eligible']+3*76000)
    print('TRAIN_AUDIT',json.dumps(dict(counts)),flush=True)
    report = {'checkpoint_sha256': protected[ckpt], 'selection': metadata['selection'],
              'train_counts':dict(counts),'audited_train_prefix_rows':256,'eligible_prefix_profiles':audit,
              'validation_policy':'first8 sum-eligible validation records from index128; fixed before output inspection',
              'validation_indices':[i for i,_ in chosen],'prompt_parity_checked':len(audit),
              'test_data_used':False,'three_video_clips_used_for_selection':False,'records':[]}
    original_generate = model.generate
    traces = []

    def generate(prompt, *args, **kwargs):
        output = original_generate(prompt,*args,**kwargs)
        new = output[0,prompt.shape[1]:].tolist()
        traces.append({'prompt_ids':prompt[0].tolist(),'prompt_tokens':prompt.shape[1],
                       'input':tok.decode(prompt[0,:-1].tolist()),'output':tok.decode(new).strip(),
                       'new_tokens':len(new),'eos_stop':bool(new and new[-1]==tok.special_tokens['<eos>'])})
        return output

    model.generate = generate
    with torch.inference_mode():
        for index,row in chosen:
            traces.clear()
            full = services._real_summarize(schemas.CompletionRequest(prompt=row['body'],temperature=0,max_tokens=96))
            full_trace = list(traces)
            prefix = tok.encode('<sum>')
            capacity = 512-96-1-len(prefix)
            source_ids = tok.encode(' '+row['body'])
            assert full_trace[0]['prompt_ids'] == summary_prompt_ids(row['body'],tok,'sum',512,96)
            if len(source_ids)>capacity:
                mapped = full_trace[:math.ceil(len(source_ids)/capacity)]
                assert list(itertools.chain.from_iterable(t['prompt_ids'][len(prefix):-1] for t in mapped)) == source_ids
            target = tok.decode(tok.encode(row['summary'])[:95])
            visible = tok.decode(source_ids[:capacity]).strip()
            lead = re.split(r'(?<=[.!?])\s+',visible,maxsplit=1)[0]
            ds = SummaryPairDataset([(row['body'],row['summary'])],tok,fmt='sum',context_len=512,max_target_tokens=96)
            x,y = ds[0]
            prompt = summary_prompt_ids(row['body'],tok,'sum',512,96)
            assert y[:len(prompt)-1].eq(-100).all() and y[-1].item()==tok.special_tokens['<eos>']
            loss = minigpt_loss(model,(x[None],y[None])).item()
            title_prompt = summary_prompt_ids((row['summary']+' '+row['body']).strip(),tok,'title',512,96)
            title_ids = original_generate(torch.tensor([title_prompt]),96,temperature=0,eos_id=tok.special_tokens['<eos>'])
            title = tok.decode(title_ids[0,len(title_prompt):].tolist()).strip()
            if not report['records']:
                short = torch.tensor([prompt])
                cached = original_generate(short,8,temperature=0,eos_id=tok.special_tokens['<eos>'])
                reference = short
                for _ in range(cached.shape[1]-short.shape[1]):
                    logits,_ = model(reference)
                    reference = torch.cat([reference,logits[:,-1].argmax(-1,keepdim=True)],dim=1)
                assert torch.equal(cached,reference), 'KV-cache greedy/full-forward mismatch'
                report['real_checkpoint_cache_full_forward_parity_8steps'] = True
            item = {'validation_index':index,'id':row['id'],'source':row['body'],'reference_summary':row['summary'],
                    'target_visible_to_training':target,'reference_title':row['title'],'profile':source_profile(row,tok),
                    'training_prompt_and_mask_pass':True,'teacher_forced_sum_loss':loss,
                    'sum_direct_visible_prefix':full_trace[0]['output'],'sum_full_service':full,
                    'title_direct_visible_prefix':title,'full_service_calls':len(full_trace),'trace':full_trace,
                    'summary_rouge_l_full_reference':rouge_l(row['summary'],full),
                    'prefix_summary_rouge_l_capped_reference':rouge_l(target,full_trace[0]['output']),
                    'lead1_rouge_l_capped_reference':rouge_l(target,lead),
                    'title_rouge_l':rouge_l(row['title'],title),
                    'summary_full_repeated_trigram_fraction':repeated_trigram_fraction(full),
                    'summary_prefix_repeated_trigram_fraction':repeated_trigram_fraction(full_trace[0]['output'])}
            assert math.isfinite(loss)
            report['records'].append(item)
            save(OUT/'diagnostic.json',report)
            print('VALIDATION',index,'tokens',len(source_ids),'calls',len(full_trace),'prefix/full repeat',round(item['summary_prefix_repeated_trigram_fraction'],3),round(item['summary_full_repeated_trigram_fraction'],3),flush=True)
    model.generate = original_generate
    assert len(report['records'])==8 and all(sha(p)==v for p,v in protected.items())
    report['status']='DIAGNOSTIC COMPLETE - NO WEIGHT OR PRODUCTION CHANGES'
    report['services_sha256']=sha(ROOT/'inference-service/app/services.py')
    report['script_sha256']=sha(Path(__file__))
    save(OUT/'diagnostic.json',report)
    save(ROOT/'data/manifests/minigpt_pipeline_diagnostic.json',{k:v for k,v in report.items() if k not in ['records','eligible_prefix_profiles']}|{'packet':str(OUT)})
    print('COMPLETE',OUT,flush=True)


if __name__=='__main__':
    main()
