import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('train_error_audit', Path(__file__).with_name('audit_train.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.mark.parametrize('reference,hypothesis,expected', [
    ('FTA 2020', 'FTA 2020', {'C': 2}), ('FTA 2020', 'FTA 2021', {'C': 1, 'S': 1}),
    ('FTA 2020', 'FTA', {'C': 1, 'D': 1}), ('FTA', 'FTA FTA', {'C': 1, 'I': 1}),
    ('', 'FTA', {'I': 1}), ('FTA', '', {'D': 1}), ('', '', {})])
def test_alignment_operations_account_for_every_word(reference, hypothesis, expected):
    from collections import Counter
    assert dict(Counter(x['op'] for x in audit.align_words(reference, hypothesis))) == expected


def test_cue_span_requires_all_words_and_no_insertion_inside_phrase():
    ref = 'HÀ NỘI FDI 08/2020 THÔNG TƯ DOANH NGHIỆP'
    same = audit.cue_matches(ref, audit.align_words(ref, ref))
    assert all(s['exact_word_span'] for group in same.values() for s in group)
    inserted = audit.cue_matches(ref, audit.align_words(ref, 'HÀ VÀ NỘI FDI 08/2020 THÔNG TƯ DOANH NGHIỆP'))
    assert inserted['place_cue'][0]['exact_word_span'] is False
    changed = audit.cue_matches(ref, audit.align_words(ref, 'HÀ NỘI FDI 09/2020 THÔNG TƯ DOANH NGHIỆP'))
    assert changed['numeric_surface'][0]['exact_word_span'] is False


def test_summary_keeps_raw_numbers_punctuation_and_overlapping_cues():
    rows = [{'sample_id': 'train', 'reference': 'FDI 08/2020,', 'hypothesis': 'FDI 09/2020'}]
    result = audit.summarize(rows)
    assert result['metrics']['word_errors'] == 1
    assert result['word_operations'] == {'C': 1, 'S': 1}
    assert result['cue_groups']['english_acronym_cue']['exact_spans'] == 1
    assert result['cue_groups']['numeric_surface']['exact_spans'] == 0
    assert rows[0]['reference'] == 'FDI 08/2020,'
    empty = audit.summarize([{'sample_id': 'train', 'reference': 'FDI 2020', 'hypothesis': ''}])
    assert empty['metrics']['word_errors'] == 2 and empty['word_operations'] == {'D': 2}
