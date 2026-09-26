"""Dẫn xuất JPEG cho Siamese phải giữ nguyên tính chất cặp dương của dataset_spec §3.2.

Rủi ro chính không phải crash mà là **hỏng âm thầm**: subsample thưa hơn 10s thì mọi frame liền kề
đều ngoài cửa sổ 1–10s, `SiamesePairDataset` rơi hết về fallback augment-cùng-frame, và model chỉ
học so màu chứ không học ngữ nghĩa. Recall@10 vẫn ra một con số, không có gì báo lỗi.
"""

import json

import pytest


def _make_manifest(tmp_path, secs, group="g00h1"):
    from PIL import Image

    src = tmp_path / "png"
    src.mkdir()
    items = []
    for s in secs:
        p = src / f"{group}_s{s:05d}.png"
        Image.new("RGB", (398, 224), (s % 256, 40, 200)).save(p)
        items.append({"path": str(p), "label": "bong_da", "split": "train",
                      "group": group, "extra": {"sec": s, "checksum": "x"}})
    m = tmp_path / "src.json"
    m.write_text(json.dumps({"items": items, "meta": {"fps": 1}}), encoding="utf-8")
    return m


def _run(monkeypatch, manifest, out, out_manifest, every):
    from ai_core.scripts import build_siamese_subset

    monkeypatch.setattr("sys.argv", [
        "build_siamese_subset", "--manifest", str(manifest), "--out", str(out),
        "--out-manifest", str(out_manifest), "--every", str(every)])
    build_siamese_subset.main()


def test_every_above_pair_window_is_refused(tmp_path, monkeypatch):
    """--every 15 > 10s: phải chặn, không được chạy rồi sinh dataset vô dụng."""
    m = _make_manifest(tmp_path, range(0, 60))
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, m, tmp_path / "jpg", tmp_path / "out.json", 15)
    assert "dataset_spec §3.2" in str(e.value)


def test_subsample_keeps_every_nth_second_and_resizes(tmp_path, monkeypatch):
    """Không assert kích thước byte ở đây: fixture là ảnh màu PHẲNG, PNG nén xuống gần 0 nên JPEG
    còn to hơn. Mức giảm thật đo trên frame SoccerNet 398×224: PNG 105 KB → JPEG q90 23 KB.
    Cái test được ở đây là logic của script: giữ đúng giây nào, resize bao nhiêu, đuôi file gì.
    """
    m = _make_manifest(tmp_path, range(0, 60))
    out_manifest = tmp_path / "out.json"
    _run(monkeypatch, m, tmp_path / "jpg", out_manifest, 5)

    kept = json.loads(out_manifest.read_text(encoding="utf-8"))["items"]
    assert [i["extra"]["sec"] for i in kept] == list(range(0, 60, 5))
    assert all(i["path"].endswith(".jpg") for i in kept)
    assert all(i["group"] == "g00h1" and i["label"] == "bong_da" for i in kept)

    from PIL import Image
    assert Image.open(kept[0]["path"]).size == (224, 224)      # đúng img_size của ViT
    assert Image.open(kept[0]["extra"]["src"]).size == (398, 224)   # bản gốc giữ nguyên


def test_gap_after_subsample_stays_inside_pair_window(tmp_path, monkeypatch):
    """Bất biến thật sự cần: 2 frame liền kề cách ≤ 10s để cặp dương còn sinh được."""
    m = _make_manifest(tmp_path, range(0, 60))
    out_manifest = tmp_path / "out.json"
    _run(monkeypatch, m, tmp_path / "jpg", out_manifest, 5)

    secs = [i["extra"]["sec"] for i in json.loads(out_manifest.read_text(encoding="utf-8"))["items"]]
    gaps = [b - a for a, b in zip(secs, secs[1:])]
    assert gaps and max(gaps) <= 10


def test_zero_filled_leftover_is_regenerated_not_trusted(tmp_path, monkeypatch):
    """Đã cắn thật: kill process giữa lúc chạy để lại cả group file có kích thước hợp lý nhưng nội
    dung TOÀN BYTE 0. Lần chạy sau thấy file tồn tại nên bỏ qua, và 2.777 frame rác đi thẳng vào
    embedding — không gì báo. Guard phải kiểm SOI marker, không chỉ kiểm tồn tại.
    """
    from PIL import Image

    m = _make_manifest(tmp_path, [0, 5])
    out = tmp_path / "jpg"
    (out / "g00h1").mkdir(parents=True)
    rac = out / "g00h1" / "g00h1_s00000.jpg"
    rac.write_bytes(b"\0" * 14000)                             # kích thước hợp lý, nội dung rác

    _run(monkeypatch, m, out, tmp_path / "out.json", 5)

    assert rac.read_bytes()[:3] == b"\xff\xd8\xff"             # đã ghi lại thật
    assert Image.open(rac).size == (224, 224)
    assert not list((out / "g00h1").glob("*.tmp"))             # không để lại file trung gian


def test_shards_cover_every_group_exactly_once(tmp_path, monkeypatch):
    """Chia song song phải theo GROUP và rời nhau tuyệt đối. Hai process cùng ghi một file JPEG thì
    cả hai đều qua `os.path.exists` rồi ghi chồng nhau → file hỏng mà không báo gì.
    """
    from ai_core.data import load_manifest, save_manifest
    from ai_core.scripts import build_siamese_subset

    items = []
    groups = [f"g{i:02d}h1" for i in range(8)]
    for g in groups:
        (tmp_path / g).mkdir()                                 # _make_manifest không tạo parents
        items += load_manifest(_make_manifest(tmp_path / g, [0, 5], group=g))
    merged = tmp_path / "all.json"
    save_manifest(merged, items, meta={"fps": 1})

    N = 3
    per_shard = []
    for shard in range(N):
        out_manifest = tmp_path / f"part{shard}.json"
        monkeypatch.setattr("sys.argv", [
            "build_siamese_subset", "--manifest", str(merged), "--out", str(tmp_path / "jpg"),
            "--out-manifest", str(out_manifest), "--every", "5",
            "--num-shards", str(N), "--shard", str(shard)])
        build_siamese_subset.main()
        per_shard.append({i.group for i in load_manifest(out_manifest)})

    assert sum(len(s) for s in per_shard) == len(groups)       # không group nào làm hai lần
    assert set().union(*per_shard) == set(groups)              # không group nào bị bỏ


def test_empty_result_fails_loudly(tmp_path, monkeypatch):
    """Không frame nào chia hết cho --every → phải nổ, không ghi manifest rỗng."""
    m = _make_manifest(tmp_path, [1, 2, 3])
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, m, tmp_path / "jpg", tmp_path / "out.json", 5)
    assert "Không giữ được frame nào" in str(e.value)
