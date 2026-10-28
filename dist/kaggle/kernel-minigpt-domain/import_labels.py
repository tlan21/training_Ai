"""Only human-authored, attested labels with matching immutable media may be exported."""
import argparse
import json
import sys
import unicodedata
from pathlib import Path

from prepare_media import ROOT,OUT,sha,save
sys.path.insert(0,str(ROOT/'ai-core'))
from ai_core.scripts.prepare_aligned_summary import has_sentence_ending
from ai_core.tokenizer import BPETokenizer
from ai_core.training.datasets.summary_dataset import summary_prompt_ids


def validate(payload, samples, packet_sha, tok):
    if payload.get('packet_sha256')!=packet_sha:
        raise ValueError('stale/wrong annotation packet hash')
    rows = payload.get('records',[])
    expected = {r['sample_id']:r for r in samples}
    ids = [r['sample_id'] for r in rows]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):
        raise ValueError('duplicate/missing/unknown sample IDs')
    parts = {'train':[],'val':[]}
    # D22 (user 2026-10-27): Claude-drafted + Claude-reviewed summaries are allowed MiniGPT targets (disclosed distillation).
    origin = 'claude_drafted_claude_reviewed' if payload.get('decision')=='D22' else 'human_written_from_audio'
    if not payload.get('annotator','').strip():
        raise ValueError('human annotator is missing; labels pending')
    for row in rows:
        item = expected[row['sample_id']]
        if origin!='human_written_from_audio' and row.get('verified') is False and row.get('reject_reason','').strip():
            continue  # explicitly rejected by the D22 reviewer
        if row.get('audio_sha256')!=item['audio_sha256'] or row.get('video_sha256')!=item['video_sha256']:
            raise ValueError('stale media hash')
        if row.get('verified') is not True or row.get('origin')!=origin or row.get('reject_reason','').strip():
            raise ValueError(f"{row['sample_id']}: human-written/audio/language/support attestation pending or rejected")
        transcript,summary = (unicodedata.normalize('NFC',row.get(k,'')).strip() for k in ('transcript','summary'))
        if len(transcript.split())<5 or len(summary.split())<5 or not has_sentence_ending(summary):
            raise ValueError(f"{row['sample_id']}: missing/full transcript or incomplete summary")
        if '[không rõ]' in transcript.casefold() or '[không rõ]' in summary.casefold():
            raise ValueError('unclear audio must be rejected/resegmented, never guessed')
        if len(tok.encode(summary))+1>96:
            raise ValueError('summary exceeds95 BPE tokens; never silently truncate labels')
        if set(item['asr_inputs'])!={'active','candidate'}:
            raise ValueError('both own-ASR input variants are required')
        inputs = {'human':transcript,**{name:v['text'] for name,v in item['asr_inputs'].items()}}
        normalized = {}
        for name,text in inputs.items():
            text = text.strip()
            text = text.lower() if text.isupper() else text
            if not text or len(summary_prompt_ids(text,tok,'sum',512,96))!=len(tok.encode('<sum> '+text))+1:
                raise ValueError(f"{row['sample_id']}/{name}: empty or over-budget input; needs new clip version")
            normalized[name] = text
        parts[item['split']].append({'id':row['sample_id'],'video_id':item['video_id'],
            'channel_id':item['channel_id'],'audio_sha256':item['audio_sha256'],'video_sha256':item['video_sha256'],
            'human_transcript':transcript,'summary':summary,'inputs':normalized,
            'annotator':payload['annotator'].strip(),'label_origin':origin,
            'speaker_id':row.get('speaker_id','').strip() or None})
    for key in ('video_id','channel_id','speaker_id'):
        left = {r[key] for r in parts['train'] if r[key]}
        right = {r[key] for r in parts['val'] if r[key]}
        if left & right:
            raise ValueError(f'{key} overlaps train/validation')
    if not parts['train'] or not parts['val']:
        raise ValueError('both fixed splits require human labels')
    for key in ('human_transcript','summary'):
        left = {' '.join(r[key].casefold().split()) for r in parts['train']}
        right = {' '.join(r[key].casefold().split()) for r in parts['val']}
        if left & right:
            raise ValueError(f'exact {key} duplicate across train/validation; review source grouping')
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels',required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT/'data/manifests/minigpt_real_domain.json').read_text(encoding='utf-8'))
    assert sha(OUT/'samples.json')==manifest['samples_sha256']
    assert sha(OUT/'sources.json')==manifest['sources_sha256']
    assert sha(OUT/'selection.json')==manifest['selection_sha256']
    samples = json.loads((OUT/'samples.json').read_text(encoding='utf-8'))
    for row in samples:
        assert sha(OUT/row['audio'])==row['audio_sha256'] and sha(OUT/row['video'])==row['video_sha256']
    frozen = json.loads((OUT/'frozen_guard.json').read_text(encoding='utf-8'))
    assert all(sha(p)==v for p,v in frozen.items())
    payload = json.loads(Path(args.labels).read_text(encoding='utf-8-sig'))
    vocab = ROOT/'ai-core/checkpoints/minigpt/bpe_vocab.json'
    assert sha(vocab)==manifest['vocab_sha256']
    tok = BPETokenizer.load(str(vocab))
    try:
        parts = validate(payload,samples,manifest['samples_sha256'],tok)
    except ValueError as error:
        parser.exit(1,f'NOT TRAINING READY: {error}\n')
    target = OUT/('accepted_'+sha(Path(args.labels))[:12])
    target.mkdir(exist_ok=False)
    for split,rows in parts.items():
        save(target/f'domain_{split}.json',rows)
    save(target/'labels_provenance.json',{'source_labels':str(Path(args.labels).resolve()),'source_sha256':sha(Path(args.labels)),
         'packet_sha256':manifest['samples_sha256'],'vocab_sha256':sha(vocab),'annotator':payload['annotator'],
         'label_attestation':('D22: Claude-drafted, Claude-reviewed summaries (disclosed distillation; not human labels)'
                              if payload.get('decision')=='D22' else 'User-supplied attestation; not an independent semantic audit'),
         'decision':payload.get('decision'),
         'counts':{k:len(v) for k,v in parts.items()},'training_run':False,'protocol':'real-domain-human-v1'})
    print('Labels structurally verified/exported:',target,'No training or deployment.')


if __name__=='__main__':
    main()
