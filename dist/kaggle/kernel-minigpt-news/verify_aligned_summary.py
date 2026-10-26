"""Verify prepared pairs and measure existing weights; no training or human annotations."""
import json
import sys
from pathlib import Path

from transcribe_pretrained_drafts import ROOT, save, sha

sys.path[:0] = [str(ROOT/'ai-core'), str(ROOT/'inference-service')]
DATA = Path('D:/data_training_ai/minigpt_news/aligned_summary_v2_20261019')


def main():
    import torch
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.data.manifest import file_checksum
    from ai_core.tokenizer import BPETokenizer
    from ai_core.training.checkpoint import load_checkpoint
    from ai_core.training.datasets.summary_dataset import summary_prompt_ids
    from ai_core.scripts.finetune_news_summary import aligned_source, aligned_validation, encoded_dataset, validate_aligned_bundle
    from app import schemas, services
    from app.registry import registry

    torch.set_num_threads(2)
    torch.manual_seed(1337)
    output = DATA/'baseline_current_checkpoint.json'
    assert not output.exists()
    manifest = json.loads((DATA/'news_manifest.json').read_text(encoding='utf-8'))
    parts = {s:json.loads((DATA/f'news_{s}.json').read_text(encoding='utf-8')) for s in ('train','val')}
    for s,rows in parts.items():
        assert len(rows) == manifest['splits'][s]['count']
        assert file_checksum(str(DATA/f'news_{s}.json')) == manifest['splits'][s]['sha1']
        assert len({r['id'] for r in rows}) == len(rows)
    assert len(parts['val']) == 64
    assert not {r['id'] for r in parts['train']} & {r['id'] for r in parts['val']}
    assert [r['id'] for r in parts['val']] == manifest['validation_ids']
    try:
        validate_aligned_bundle(DATA, manifest, parts['train'], parts['val'])
    except ValueError as e:
        assert 'human audit pending' in str(e) or 'summaries have invalid sentence endings' in str(e)
        audit_gate = str(e)
    else:
        raise AssertionError('blank human annotations must block training')
    vocab = Path(manifest['parent_directory'])/'bpe_vocab.json'
    assert file_checksum(str(vocab)) == manifest['vocab_sha1']
    tok = BPETokenizer.load(str(vocab))
    checked = 0
    for noisy in (False, True):
        rows = parts['train']+parts['val']
        items = encoded_dataset(rows, tok, noisy, aligned=True)
        n = len(rows)
        for group,fmt in enumerate(('title','title','sum','cap')):
            for row,(x,y) in zip(rows,items[group*n:(group+1)*n]):
                source = aligned_source(row,noisy)
                prompt = summary_prompt_ids(source,tok,fmt,512,96)
                assert len(prompt) == len(tok.encode(f'<{fmt}> '+source))+1
                assert x[:len(prompt)].tolist() == prompt
                assert y[:len(prompt)-1].eq(-100).all()
                target = row['summary'] if fmt=='sum' else row['title']
                assert y[len(prompt)-1:].tolist() == tok.encode(target)+[tok.special_tokens['<eos>']]
                checked += 1
        del items
    ckpt = ROOT/'ai-core/checkpoints/minigpt/best.pt'
    protected = sha(ckpt)
    assert protected == 'cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac'
    saved = load_checkpoint(str(ckpt))
    model = build_model('minigpt', ModelConfig(**saved['config'])).eval()
    model.load_state_dict(saved['state_dict'],strict=True)
    registry.models['minigpt'], registry.device = model, 'cpu'
    registry.minigpt_metadata = saved['metadata']
    registry.tokenizer = registry._rebuild_tokenizer(saved['bpe_vocab'])
    assert registry.tokenizer.merges == tok.merges and registry.tokenizer.special_tokens == tok.special_tokens
    del saved
    generate, calls = model.generate, 0

    def progress(*args, **kwargs):
        nonlocal calls
        result = generate(*args, **kwargs)
        calls += 1
        if calls % 16 == 0:
            print('BASELINE_GENERATIONS',calls,'/256 +4 service parity',flush=True)
        return result

    model.generate = progress
    with torch.inference_mode():
        score, metrics, predictions = aligned_validation(model,parts['val'],tok,torch.device('cpu'))
        for noisy,key in ((False,'sum_clean'),(True,'sum_asr')):
            for row,pred in zip(parts['val'][:2],predictions[key][:2]):
                value = services._real_summarize(schemas.CompletionRequest(
                    prompt=aligned_source(row,noisy),temperature=0,max_tokens=96))
                assert value == pred['prediction'], 'training-eval/production output mismatch'
    model.generate = generate
    assert sha(ckpt) == protected and calls == 260
    report = {'status':'PREPARATION_VERIFIED_BASELINE_ONLY_HUMAN_AUDIT_PENDING',
              'checkpoint_sha256':protected, 'manifest_sha256':sha(DATA/'news_manifest.json'),
              'encoded_pair_checks':checked, 'n_train':len(parts['train']), 'n_val':len(parts['val']),
              'training_gate':audit_gate, 'production_parity_cases':4,
              'selection_score':score,'metrics':metrics,'predictions':predictions,
              'weights_changed':False,'trained':False,'script_sha256':sha(Path(__file__)),
              'trainer_sha256':sha(ROOT/'ai-core/ai_core/scripts/finetune_news_summary.py'),
              'preparer_sha256':sha(ROOT/'ai-core/ai_core/scripts/prepare_aligned_summary.py')}
    save(output,report)
    save(ROOT/'data/manifests/minigpt_aligned_summary.json',
         {k:v for k,v in report.items() if k!='predictions'} | {'directory':str(DATA),'dataset':manifest})
    print('COMPLETE',json.dumps(metrics),flush=True)


if __name__=='__main__':
    main()
