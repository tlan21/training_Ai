"""Bất biến quan trọng nhất: tên gNNhH ĐÃ GÁN không bao giờ đổi khi thêm trận mới.

Nhãn/giây, manifest, embedding 256-d và checkpoint đều tham chiếu tên này. Nếu thêm 60 trận mà
`g04h2` trỏ sang trận khác thì mọi thứ vẫn chạy trót lọt và ra số vô nghĩa — không gì báo lỗi.
"""

import json

import pytest


def _make_game(root, league, season, name, halves=("1", "2")):
    d = root / league / season / name
    d.mkdir(parents=True, exist_ok=True)
    for h in halves:
        (d / f"{h}_224p.mkv").write_bytes(b"x")
    return f"{league}/{season}/{name}"


def _run(monkeypatch, root, flat, labels):
    from ai_core.scripts import flatten_soccernet

    monkeypatch.setattr("sys.argv", ["flatten_soccernet", "--root", str(root),
                                     "--flat", str(flat), "--labels-out", str(labels)])
    flatten_soccernet.main()
    return (json.loads((flat / "_mapping.json").read_text(encoding="utf-8")),
            json.loads(labels.read_text(encoding="utf-8")))


def test_assigns_ids_in_sorted_order_and_links_both_halves(tmp_path, monkeypatch):
    root, flat = tmp_path / "root", tmp_path / "flat"
    _make_game(root, "epl", "2014-2015", "b match")
    _make_game(root, "epl", "2014-2015", "a match")
    mapping, labels = _run(monkeypatch, root, flat, tmp_path / "labels.json")

    assert mapping["g00h1"]["game"].endswith("a match")     # theo thứ tự tên, không phải thứ tự tạo
    assert mapping["g01h1"]["game"].endswith("b match")
    assert sorted(mapping) == ["g00h1", "g00h2", "g01h1", "g01h2"]
    assert all((flat / f"{s}.mkv").exists() for s in mapping)
    assert labels == {s: "bong_da" for s in mapping}


def test_adding_games_never_renumbers_existing_ones(tmp_path, monkeypatch):
    root, flat, lab = tmp_path / "root", tmp_path / "flat", tmp_path / "labels.json"
    _make_game(root, "epl", "2014-2015", "m2")
    first, _ = _run(monkeypatch, root, flat, lab)

    # Trận mới đứng TRƯỚC theo alphabet: gán lại từ đầu thì nó chiếm g00 và đẩy m2 sang g01.
    _make_game(root, "epl", "2014-2015", "m1")
    second, _ = _run(monkeypatch, root, flat, lab)

    assert second["g00h1"]["game"] == first["g00h1"]["game"]
    assert second["g01h1"]["game"].endswith("m1")
    assert len(second) == 4


def test_game_missing_a_half_is_skipped(tmp_path, monkeypatch):
    """Chỉ có hiệp 1 thì bỏ hẳn: nửa trận lọt vào pipeline sẽ nổ ở bước sau."""
    root, flat = tmp_path / "root", tmp_path / "flat"
    _make_game(root, "epl", "2014-2015", "full")
    _make_game(root, "epl", "2014-2015", "half only", halves=("1",))
    mapping, _ = _run(monkeypatch, root, flat, tmp_path / "labels.json")

    assert len(mapping) == 2
    assert all(v["game"].endswith("full") for v in mapping.values())


def test_no_games_writes_empty_mapping(tmp_path, monkeypatch):
    root, flat = tmp_path / "root", tmp_path / "flat"
    root.mkdir()
    mapping, labels = _run(monkeypatch, root, flat, tmp_path / "labels.json")
    assert mapping == {} and labels == {}


def test_label_key_matches_build_soccernet_labels_convention(tmp_path, monkeypatch):
    """`label_key` phải là <game với '/'→'__'>_<half>; lệch là mất liên kết sang nhãn/giây."""
    root, flat = tmp_path / "root", tmp_path / "flat"
    game = _make_game(root, "epl", "2014-2015", "a match")
    mapping, _ = _run(monkeypatch, root, flat, tmp_path / "labels.json")
    assert mapping["g00h2"]["label_key"] == game.replace("/", "__") + "_2"


def test_hardlink_failure_is_loud(tmp_path, monkeypatch):
    """Khác volume → phải nổ, không âm thầm copy (mỗi trận tốn thêm 0,36 GB)."""
    from ai_core.scripts import flatten_soccernet

    root, flat = tmp_path / "root", tmp_path / "flat"
    _make_game(root, "epl", "2014-2015", "a match")
    monkeypatch.setattr("os.link", lambda *a: (_ for _ in ()).throw(OSError("cross-device link")))
    monkeypatch.setattr("sys.argv", ["flatten_soccernet", "--root", str(root), "--flat", str(flat),
                                     "--labels-out", str(tmp_path / "labels.json")])
    with pytest.raises(SystemExit) as e:
        flatten_soccernet.main()
    assert "hardlink" in str(e.value)
