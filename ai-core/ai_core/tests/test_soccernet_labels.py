"""Mapping 17 lớp SoccerNet → nhãn highlight/giây (phương án A).

Nhãn quyết định model học gì; sai mapping thì mọi F1 sau đó vô nghĩa mà không test nào khác phát
hiện. Nên khoá đủ 4 tính chất: cửa sổ dilation, viền IGNORE, thứ tự ưu tiên dương-thắng-ambiguous,
và "không lên hình" thì không được thành nhãn dương.
"""

from ai_core.data.weak_label import IGNORE
from ai_core.scripts.build_soccernet_labels import half_length, labels_for_half


def _ann(half: str, sec: int, label: str, visibility: str = "visible") -> dict:
    return {"gameTime": f"{half} - 00:{sec:02d}", "label": label,
            "position": str(sec * 1000), "visibility": visibility}


def test_positive_event_covers_dilation_window_with_ignore_rim():
    labels = labels_for_half([_ann("1", 30, "Goal")], half="1", n_seconds=60, dilation_sec=5)

    assert labels[25:36] == [1] * 11               # ±5s quanh giây 30
    assert labels[24] == IGNORE and labels[36] == IGNORE   # viền: cắt lệch thì phạt oan
    assert labels[23] == 0 and labels[37] == 0     # ngoài viền là âm thật
    assert labels[:23] == [0] * 23


def test_ambiguous_class_is_ignore_not_negative():
    """Thẻ vàng/corner đài có lúc cắt vào highlight có lúc không — gán 0 là dạy model sai."""
    labels = labels_for_half([_ann("1", 10, "Yellow card")], half="1", n_seconds=30, dilation_sec=2)
    assert labels[10] == IGNORE
    assert labels.count(IGNORE) == 1               # không lan ra, chỉ đúng giây đó


def test_plain_gameplay_class_is_negative():
    labels = labels_for_half([_ann("1", 10, "Throw-in"), _ann("1", 20, "Ball out of play")],
                             half="1", n_seconds=30, dilation_sec=2)
    assert labels == [0] * 30


def test_positive_wins_over_ambiguous_on_same_second():
    """Corner ngay giây có Goal phải là 1. Ghi sai thứ tự thì giây quan trọng nhất của cả trận
    thành IGNORE và không đóng góp gradient."""
    labels = labels_for_half([_ann("1", 20, "Corner"), _ann("1", 20, "Goal")],
                             half="1", n_seconds=40, dilation_sec=3)
    assert labels[20] == 1


def test_not_shown_positive_becomes_ignore_not_positive():
    """Hành động không lên hình → nhánh visual không có gì để học; gán 1 là dạy đoán từ hư không."""
    labels = labels_for_half([_ann("1", 20, "Goal", visibility="not shown")],
                             half="1", n_seconds=40, dilation_sec=3)
    assert 1 not in labels
    assert labels[17:24] == [IGNORE] * 7


def test_other_half_events_do_not_leak():
    """position là millisecond TRONG HIỆP nên giây 30 có ở cả hai hiệp — lọc sai là trộn nhãn."""
    labels = labels_for_half([_ann("2", 30, "Goal")], half="1", n_seconds=60, dilation_sec=5)
    assert labels == [0] * 60


def test_event_beyond_half_length_is_dropped_not_crashing():
    labels = labels_for_half([_ann("1", 500, "Goal")], half="1", n_seconds=60, dilation_sec=5)
    assert labels == [0] * 60


def test_dilation_window_is_clipped_at_half_boundaries():
    labels = labels_for_half([_ann("1", 1, "Goal")], half="1", n_seconds=10, dilation_sec=5)
    assert len(labels) == 10                       # không tràn mảng
    assert labels[0] == 1 and labels[6] == 1


def test_half_length_uses_last_annotation_plus_pad():
    anns = [_ann("1", 10, "Goal"), _ann("1", 40, "Throw-in"), _ann("2", 90, "Goal")]
    assert half_length(anns, "1", pad_sec=30) == 70
    assert half_length(anns, "2", pad_sec=30) == 120
    assert half_length(anns, "3", pad_sec=30) == 30      # hiệp không có nhãn → chỉ còn pad


# ---------------------------------------------------------------- --mapping: đặt tên file theo stem

def _game(tmp_path, rel="lg/2014-2015/m"):
    import json

    d = tmp_path / "sn" / rel
    d.mkdir(parents=True)
    (d / "Labels-v2.json").write_text(json.dumps({
        "UrlLocal": rel,
        "annotations": [_ann("1", 40, "Goal"), _ann("2", 40, "Goal")],
    }), encoding="utf-8")
    return rel


def _run(monkeypatch, tmp_path, mapping=None):
    import json

    from ai_core.scripts import build_soccernet_labels

    argv = ["build_soccernet_labels", "--soccernet", str(tmp_path / "sn"),
            "--out", str(tmp_path / "out")]
    if mapping is not None:
        p = tmp_path / "_mapping.json"
        p.write_text(json.dumps(mapping), encoding="utf-8")
        argv += ["--mapping", str(p)]
    monkeypatch.setattr("sys.argv", argv)
    build_soccernet_labels.main()
    return sorted(f.stem for f in (tmp_path / "out").glob("*.json"))


def test_without_mapping_filenames_stay_label_keys(tmp_path, monkeypatch):
    """Hành vi cũ phải giữ nguyên khi không truyền --mapping."""
    _game(tmp_path)
    assert _run(monkeypatch, tmp_path) == ["lg__2014-2015__m_1", "lg__2014-2015__m_2"]


def test_mapping_renames_to_stem_and_drops_halves_without_video(tmp_path, monkeypatch):
    """Ghi thẳng tên gNNhH (build_highlight_features tìm '<stem>.json'), và bỏ hiệp chưa tải video —
    trước đây bước đổi tên làm bằng tay nên không gì kiểm được hai điều này."""
    rel = _game(tmp_path)
    mapping = {"g07h1": {"game": rel, "half": "1", "label_key": f"{rel.replace('/', '__')}_1"}}
    assert _run(monkeypatch, tmp_path, mapping) == ["g07h1"]      # hiệp 2 không có trong mapping
