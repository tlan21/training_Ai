"""Retrospective train-only ASR error audit; never selects weights or edits labels."""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('D:/data_training_ai/asr_domain_replay_v1_20261021')
DOMAIN = Path('D:/data_training_ai/minigpt_domain_v1_20261019')
sys.path[:0] = [str(ROOT / 'ai-core'), str(ROOT / 'inference-service'), str(ROOT / 'dist/kaggle/kernel-minigpt-news')]
from ai_core.scripts.prepare_asr_robust import sha
from ai_core.scripts.evaluate import edit_distance
from diagnose_asr_reference import reference_metrics

# Lexical cues are screening aids, not verified language/entity annotations.
CUES = {
    'english_acronym_cue': r'\b(?:GDP|FDI|CPI|FTA|WTO|ASEAN|OCOP|APEC|UNESCO|UNICEF|ODA|USD|EU|LOGISTICS|ONLINE|MARKETING|STARTUP|FACEBOOK|GOOGLE|APPLE)\b',
    'numeric_surface': r'(?<!\w)\d+(?:[.,/:%-]\d+)*(?:%)?(?!\w)',
    'legal_cue': r'\b(?:THÔNG TƯ|NGHỊ QUYẾT|NGHỊ ĐỊNH|QUYẾT ĐỊNH|LUẬT|(?:ĐIỀU|KHOẢN)\s+\d+)\b',
    'place_cue': r'\b(?:HÀ NỘI|HỒ CHÍ MINH|BÌNH DƯƠNG|VIỆT NAM|ĐÀ NẴNG|QUẢNG NINH|ĐỒNG NAI|NHẬT BẢN|TRUNG QUỐC|THÁI NGUYÊN)\b',
    'multiword_term_cue': r'\b(?:CHUYỂN ĐỔI SỐ|THƯƠNG MẠI ĐIỆN TỬ|CÔNG NGHỆ THÔNG TIN|TRÍ TUỆ NHÂN TẠO|GIÁO DỤC|CHỨNG KHOÁN|DOANH NGHIỆP|TĂNG TRƯỞNG|PHÁP LUẬT|ĐẦU TƯ)\b',
}


def align_words(reference, hypothesis):
    left, right = reference.split(), hypothesis.split()
    table = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for i in range(len(left) + 1):
        table[i][0] = i
    for j in range(len(right) + 1):
        table[0][j] = j
    for i in range(1, len(left) + 1):
        for j in range(1, len(right) + 1):
            table[i][j] = min(table[i-1][j]+1, table[i][j-1]+1, table[i-1][j-1]+(left[i-1] != right[j-1]))
    i, j, result = len(left), len(right), []
    while i or j:
        if i and j and table[i][j] == table[i-1][j-1] + (left[i-1] != right[j-1]):
            result.append({'op': 'C' if left[i-1] == right[j-1] else 'S', 'ref_index': i-1, 'hyp_index': j-1,
                           'reference': left[i-1], 'hypothesis': right[j-1]})
            i, j = i-1, j-1
        elif i and table[i][j] == table[i-1][j] + 1:
            result.append({'op': 'D', 'ref_index': i-1, 'hyp_index': None, 'reference': left[i-1], 'hypothesis': ''})
            i -= 1
        else:
            result.append({'op': 'I', 'ref_index': None, 'hyp_index': j-1, 'reference': '', 'hypothesis': right[j-1]})
            j -= 1
    result.reverse()
    assert sum(x['op'] != 'C' for x in result) == table[-1][-1] == edit_distance(left, right)
    assert sum(x['op'] != 'I' for x in result) == len(left)
    assert sum(x['op'] != 'D' for x in result) == len(right)
    return result


def cue_matches(reference, alignment):
    words = list(re.finditer(r'\S+', reference))
    by_ref = {x['ref_index']: x for x in alignment if x['ref_index'] is not None}
    result = {}
    for group, pattern in CUES.items():
        spans = []
        for match in re.finditer(pattern, reference):
            indices = [i for i, token in enumerate(words) if token.start() < match.end() and token.end() > match.start()]
            positions = [by_ref[i]['hyp_index'] for i in indices]
            exact = all(by_ref[i]['op'] == 'C' for i in indices)
            exact = exact and all(b == a + 1 for a, b in zip(positions, positions[1:]))
            spans.append({'text': match.group(), 'exact_word_span': exact})
        result[group] = spans
    return result


def summarize(rows):
    metrics = reference_metrics([{'sample_id': r['sample_id'], 'reference': r['reference'],
        'asr': {'full_transcript': r['hypothesis']}} for r in rows])
    metrics['normalization'] = 'Approved domain NFC uppercase whitespace-normalized references and raw production CTC outputs; punctuation/numbers retained; CER includes spaces.'
    counts, substitutions, deletions, insertions = [collections.Counter() for _ in range(4)]
    groups = {g: {'clips': 0, 'reference_spans': 0, 'exact_spans': 0} for g in CUES}
    for row in rows:
        alignment = align_words(row['reference'], row['hypothesis'])
        row['word_alignment'] = alignment
        row['cue_matches'] = cue_matches(row['reference'], alignment)
        for item in alignment:
            counts[item['op']] += 1
            if item['op'] == 'S': substitutions[(item['reference'], item['hypothesis'])] += 1
            elif item['op'] == 'D': deletions[item['reference']] += 1
            elif item['op'] == 'I': insertions[item['hypothesis']] += 1
        for group, spans in row['cue_matches'].items():
            groups[group]['clips'] += bool(spans)
            groups[group]['reference_spans'] += len(spans)
            groups[group]['exact_spans'] += sum(s['exact_word_span'] for s in spans)
    assert counts['S'] + counts['D'] + counts['I'] == metrics['word_errors']
    return {'metrics': metrics, 'word_operations': dict(counts), 'cue_groups': groups,
        'top_substitutions': [{'reference': a, 'hypothesis': b, 'count': n} for (a, b), n in substitutions.most_common(30)],
        'top_deletions': deletions.most_common(30), 'top_insertions': insertions.most_common(30), 'records': rows}


def main():
    import torch
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import load_checkpoint
    from app import schemas, services
    from app.registry import registry

    run = json.loads((ROOT / 'data/manifests/asr_domain_replay_training.json').read_text(encoding='utf-8'))
    assert run['status'] == 'TRAINED_OUTPUT_VERIFIED_NOT_DEPLOYED'
    intake = json.loads((ROOT / 'data/manifests/asr_verbatim_intake.json').read_text(encoding='utf-8'))
    train = json.loads((Path(intake['directory']) / 'asr_train.json').read_text(encoding='utf-8'))['items']
    assert len(train) == 30 and all(r['split'] == 'train' and r['extra']['label_origin'] == 'human_reviewed_external_asr' for r in train)
    pilot = json.loads((ROOT / 'data/manifests/asr_three_source_real_audio.json').read_text(encoding='utf-8'))
    comparison = Path(pilot['packet']) / 'comparison.json'
    assert sha(comparison) == pilot['output_hashes']['comparison.json']
    cached = {r['sample_id']: r for r in json.loads(comparison.read_text(encoding='utf-8'))['records']}
    checkpoint = BASE / 'outputs-v1/asr_domain_replay_run/asr_ctc/last.pt'
    assert sha(checkpoint) == run['last_rejected_checkpoint_sha256']
    protected = {**run['protected_hashes'], str(comparison): sha(comparison),
                 str(Path(intake['directory']) / 'asr_train.json'): sha(Path(intake['directory']) / 'asr_train.json')}
    assert all(sha(p) == h for p, h in protected.items())
    output = BASE / 'train_error_audit_20261022'
    output.mkdir(exist_ok=False)
    saved = load_checkpoint(str(checkpoint))
    assert saved['metrics']['step'] == 500 and saved['config']['n_chars'] == 134
    torch.set_num_threads(2)
    model = build_model('asr_ctc', ModelConfig(**saved['config'])).float().eval()
    model.load_state_dict(saved['state_dict'], strict=True)
    registry.device = 'cpu'
    registry.models['asr_ctc'] = model
    registry.asr_vocab = saved['metadata']['char_vocab']
    variants = {'parent133': [], 'rejected_last134': []}
    with torch.inference_mode():
        for row in train:
            sid = Path(row['path']).stem
            original = cached[sid]
            assert original['split'] == 'train' and original['audio_sha256'] == row['extra']['audio_sha256'] == sha(row['path'])
            assert original['outputs']['parent']['checkpoint_sha256'] == run['recipe']['initial_checkpoint_sha256']
            text, segments = services._real_asr(schemas.ASRRequest(audio_url=row['path'], language='vi'))
            assert isinstance(text, str) and all(0 <= s.start_time < s.end_time <= 30.02 for s in segments)
            common = {'sample_id': sid, 'reference': row['extra']['transcript'], 'channel_id': row['extra']['channel_id'],
                      'video_id': row['extra']['video_id'], 'audio_sha256': row['extra']['audio_sha256']}
            variants['parent133'].append({**common, 'hypothesis': original['outputs']['parent']['text']})
            variants['rejected_last134'].append({**common, 'hypothesis': text})
    results = {key: summarize(rows) for key, rows in variants.items()}
    for key, rows in variants.items():
        results[key]['empty_outputs'] = sum(not r['hypothesis'].strip() for r in rows)
    report = {'status': 'RETROSPECTIVE_TRAIN_AUDIT_NOT_GENERALIZATION_OR_SELECTION', 'source_labels_sha256': intake['source_labels_sha256'],
        'samples': 30, 'train_minutes': 15, 'train_channels': len({r['extra']['channel_id'] for r in train}),
        'source_video_count': len({r['extra']['video_id'] for r in train}), 'results': results,
        'cue_definitions': CUES, 'fresh_train_decodes': 30, 'hash_bound_parent_cache_reused': 30,
        'checkpoints': {'parent133': run['recipe']['initial_checkpoint_sha256'], 'rejected_last134': sha(checkpoint)},
        'protocol': 'CPU FP32 production20s windows; raw normalized reference, no punctuation/number deletion',
        'caveats': ['Last134 was fitted on these30 clips: in-sample diagnostic, not evidence of generalization.',
                    'Cue counts overlap and do not verify English/code-switch/entity coverage or acoustic correctness.',
                    'One deterministic minimum-edit alignment; substitutions are not unique causal acoustic diagnoses.'],
        'protected_hashes': protected, 'validation_or_test_scored': False, 'checkpoint_deployed': False, 'training_started': False}
    assert all(sha(p) == h for p, h in protected.items())
    (output / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {k: v for k, v in report.items() if k != 'results'}
    summary['results'] = {key: {k: v for k, v in value.items() if k != 'records'} for key, value in results.items()}
    summary['directory'] = str(output)
    summary['audit_sha256'] = sha(output / 'audit.json')
    with (ROOT / 'data/manifests/asr_train_error_audit.json').open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    print('TRAIN_AUDIT_DONE', {k: v['metrics']['macro_wer'] for k, v in results.items()}, flush=True)


if __name__ == '__main__':
    main()
