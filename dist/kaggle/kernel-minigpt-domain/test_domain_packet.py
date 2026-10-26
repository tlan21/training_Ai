import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).parent))
from prepare_media import CHANNELS,group_splits
from import_labels import validate
from build_packet import render
from ai_core.tokenizer import BPETokenizer


def fixture():
    samples = [{'sample_id':name,'video_id':name,'channel_id':name,'split':split,
                'audio_sha256':'audio-'+name,'video_sha256':'video-'+name,
                'asr_inputs':{'active':{'text':'CITY OPENS A SCHOOL TODAY'},'candidate':{'text':'city opens a new school today'}}}
               for name,split in [('a','train'),('b','val')]]
    rows = [{k:s[k] for k in ('sample_id','audio_sha256','video_sha256')} | {
        'transcript':'City opens a school for children today.' if i==0 else 'Parents visit the school with their children.',
        'summary':'A new school opens for children today.' if i==0 else 'Parents and children visit the new school.',
        'verified':True,'origin':'human_written_from_audio','reject_reason':'','speaker_id':''} for i,s in enumerate(samples)]
    return samples,{'packet_sha256':'packet','annotator':'SYNTHETIC TEST FIXTURE','records':rows}


def test_group_split_is_channel_disjoint_and_reproducible():
    parts = group_splits(CHANNELS)
    assert parts==group_splits(list(reversed(CHANNELS)))
    assert list(parts.values()).count('val')==1 and list(parts.values()).count('train')==3


def test_verified_fixture_preserves_full_text_and_both_own_asr_inputs():
    samples,payload = fixture()
    result = validate(payload,samples,'packet',BPETokenizer())
    assert len(result['train'])==len(result['val'])==1
    row = result['train'][0]
    assert row['human_transcript']==payload['records'][0]['transcript']
    assert row['summary']==payload['records'][0]['summary']
    assert set(row['inputs'])=={'human','active','candidate'}
    assert row['inputs']['active']=='city opens a school today'


@pytest.mark.parametrize('changes', [
    {'verified':False}, {'origin':'model_generated'}, {'audio_sha256':'wrong'},
    {'video_sha256':'wrong'}, {'reject_reason':'cannot hear'}, {'summary':''},
    {'summary':'A school opens for children today...'}, {'summary':'word '*100+'.'},
    {'transcript':'[không rõ] City opens a school today.'}, {'transcript':'word '*500},
])
def test_gate_refuses_pending_forged_incomplete_or_truncated_labels(changes):
    samples,payload = fixture()
    payload['records'][0].update(changes)
    with pytest.raises(ValueError):
        validate(payload,samples,'packet',BPETokenizer())


def test_gate_refuses_wrong_packet_missing_duplicate_ids_and_missing_annotator():
    samples,payload = fixture()
    variants = [dict(payload,packet_sha256='old'),dict(payload,annotator=''),
                dict(payload,records=payload['records'][:1]),
                dict(payload,records=[payload['records'][0]]*2)]
    for variant in variants:
        with pytest.raises(ValueError):
            validate(variant,samples,'packet',BPETokenizer())


@pytest.mark.parametrize('key',['channel_id','video_id','speaker_id','human_transcript','summary'])
def test_gate_refuses_cross_split_source_speaker_or_exact_label_duplicates(key):
    samples,payload = fixture()
    if key in ('channel_id','video_id'):
        samples[1][key] = samples[0][key]
    else:
        field = 'transcript' if key=='human_transcript' else key
        if key=='speaker_id':
            payload['records'][0][field] = 'same speaker'
        payload['records'][1][field] = payload['records'][0][field]
    with pytest.raises(ValueError):
        validate(payload,samples,'packet',BPETokenizer())


def test_missing_or_over_budget_asr_inputs_cannot_be_silently_omitted():
    samples,payload = fixture()
    for inputs in ({'active':{'text':'hello'}},{'active':{'text':'word '*500},'candidate':{'text':'hello'}}):
        samples[0]['asr_inputs'] = inputs
        with pytest.raises(ValueError):
            validate(payload,samples,'packet',BPETokenizer())


def test_review_embedded_json_roundtrip_is_unicode_safe_without_script_injection():
    payload = {'packet_sha256':'x','samples':[{'source_title':'</script><img src=x onerror=bad()> Tiếng Việt'}]}
    page = render(payload)
    assert '</script><img src=x' not in page
    assert json.loads(re.search(r'const packet=(.*);\nconst key=',page).group(1))==payload
    assert 'checked' not in re.sub(r'<script>.*?</script>','',page,flags=re.S)
    assert 'ASR của dự án' in page and 'không phải lời chuẩn' in page
