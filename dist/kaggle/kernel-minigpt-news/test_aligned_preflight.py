from audit_aligned_preflight import source_span


def test_evidence_offsets_are_exact_unicode_source_not_normalized_rewrite():
    source = 'Mở đầu. Hà Nội đã thu giữ 100 xe; kiểm tra tiếp.'
    result = source_span(source,'Hà Nội đã thu giữ 100 xe.')
    assert result['matched_words']==result['target_words']==7
    assert result['quote']=='Hà Nội đã thu giữ 100 xe'
    assert source[result['start']:result['end']]==result['quote']


def test_no_match_has_an_empty_source_span():
    result = source_span('abc def','xyz')
    assert result['quote']=='' and result['matched_words']==0
