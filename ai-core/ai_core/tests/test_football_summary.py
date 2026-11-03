from ai_core.scripts.compare_football_candidate import gate
from ai_core.scripts.prepare_football_summary import is_football, untag


def rows(score, lead=0.1, rep=0.0, cap=False, n=50):
    return [{"rouge_l": score + (i % 5) * 0.001, "lead1_rouge_l": lead, "repeated_trigram_fraction": rep, "cap_hit": cap}
            for i in range(n)]


def scores(candidate):
    out = {}
    for name in ("football", "general"):
        for fmt in ("sum", "title"):
            for noisy in (False, True):
                cand = candidate if (name, fmt) == ("football", "sum") else rows(0.2)
                out[(name, fmt, noisy)] = {"active": rows(0.2), "candidate": cand}
    return out


def test_gate_needs_a_real_football_gain_and_no_style_regression():
    assert gate(scores(rows(0.25)))[1]
    assert not gate(scores(rows(0.2)))[1]  # no gain over active
    assert not gate(scores(rows(0.25, lead=0.3)))[1]  # below Lead-1
    assert not gate(scores(rows(0.25, rep=0.5)))[1]  # repetition regression


def test_football_filter_and_source_tag():
    assert is_football({"category": "Thể thao", "title": "Công Phượng ghi bàn", "summary": ""})
    assert not is_football({"category": "Thể thao", "title": "Federer vô địch Wimbledon", "summary": ""})
    assert not is_football({"category": "Kinh tế", "title": "HLV trưởng", "summary": ""})
    for tagged in ("(VTC News) - Quá chán", "(TNO) Quá chán", "VOV.VN - Quá chán", "Dân Việt – Quá chán"):
        assert untag({"summary": tagged})["summary"] == "Quá chán"
    assert untag({"summary": "Tiền đạo Phan Văn Long trở lại"})["summary"] == "Tiền đạo Phan Văn Long trở lại"
