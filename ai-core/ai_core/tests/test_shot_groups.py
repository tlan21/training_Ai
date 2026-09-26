"""`group` phải là SHOT, không phải cả hiệp — dataset_spec §3.2.

Bug này đã cắn thật ở T1.3c: `group` = hiệp 2700 giây nên cặp dương cách 5–10s vắt qua cú cắt
camera, model bị dạy khớp hai ảnh không liên quan, Recall@10 chỉ 0.301. Test khoá 3 tính chất mà
nếu vỡ thì không có gì báo lỗi: cắt đúng chỗ đổi cảnh, shot quá ngắn bị loại, shot không vắt qua
hai hiệp.
"""

import json

import pytest


def _png(path, rgb):
    from PIL import Image
    Image.new("RGB", (64, 48), rgb).save(path)


def _manifest(tmp_path, frames, group="g00h1", split="train"):
    """frames: list rgb theo thứ tự giây → (đường dẫn manifest, list path ảnh)."""
    d = tmp_path / "png"
    d.mkdir(exist_ok=True)
    items = []
    for sec, rgb in enumerate(frames):
        p = d / f"{group}_s{sec:05d}.png"
        _png(p, rgb)
        items.append({"path": str(p), "label": "bong_da", "split": split,
                      "group": group, "extra": {"sec": sec, "checksum": "x"}})
    m = tmp_path / f"src_{group}.json"
    m.write_text(json.dumps({"items": items, "meta": {"fps": 1}}), encoding="utf-8")
    return m, [i["path"] for i in items]


def _run(monkeypatch, manifest, out, **kw):
    from ai_core.scripts import build_shot_groups

    argv = ["build_shot_groups", "--manifest", str(manifest), "--out-manifest", str(out)]
    for k, v in kw.items():
        argv += [f"--{k.replace('_', '-')}", str(v)]
    monkeypatch.setattr("sys.argv", argv)
    build_shot_groups.main()


def test_assign_shots_cuts_where_scene_changes(tmp_path):
    from ai_core.scripts.build_shot_groups import assign_shots

    # 3 frame đỏ, 3 xanh, 3 đỏ → đúng 3 shot.
    _, paths = _manifest(tmp_path, [(200, 20, 20)] * 3 + [(20, 20, 200)] * 3 + [(200, 20, 20)] * 3)
    assert assign_shots(paths, threshold=0.5) == [0, 0, 0, 1, 1, 1, 2, 2, 2]


def test_assign_shots_does_not_cut_inside_uniform_shot(tmp_path):
    """Cùng một cảnh thì không được cắt — cắt vụn thành shot 1 frame là mất hết cặp dương."""
    from ai_core.scripts.build_shot_groups import assign_shots

    _, paths = _manifest(tmp_path, [(120, 90, 40)] * 8)
    assert assign_shots(paths, threshold=0.5) == [0] * 8


def test_group_becomes_shot_and_short_shots_dropped(tmp_path, monkeypatch):
    # shot 0: 4 frame đỏ (giữ) | shot 1: 1 frame xanh (bỏ, <3) | shot 2: 3 frame vàng (giữ)
    m, _ = _manifest(tmp_path, [(200, 20, 20)] * 4 + [(20, 20, 200)] + [(220, 220, 30)] * 3)
    out = tmp_path / "shots.json"
    _run(monkeypatch, m, out, min_shot_frames=3)

    items = json.loads(out.read_text(encoding="utf-8"))["items"]
    assert {i["group"] for i in items} == {"g00h1_sh000", "g00h1_sh002"}   # shot 1 bị loại
    assert len(items) == 7
    assert all(i["extra"]["half"] == "g00h1" for i in items)               # giữ dấu vết hiệp gốc
    assert {i["extra"]["shot"] for i in items} == {0, 2}


def test_every_kept_shot_has_enough_frames_for_a_pair(tmp_path, monkeypatch):
    """Bất biến cần: mọi group giữ lại phải ≥ min_shot_frames, nếu không SiamesePairDataset rơi về
    augment-cùng-frame và model chỉ học so màu."""
    m, _ = _manifest(tmp_path, [(200, 20, 20)] * 4 + [(20, 20, 200)] * 2 + [(220, 220, 30)] * 5)
    out = tmp_path / "shots.json"
    _run(monkeypatch, m, out, min_shot_frames=3)

    items = json.loads(out.read_text(encoding="utf-8"))["items"]
    per_group: dict[str, int] = {}
    for i in items:
        per_group[i["group"]] = per_group.get(i["group"], 0) + 1
    assert per_group and min(per_group.values()) >= 3


def test_shot_ids_never_span_two_halves(tmp_path, monkeypatch):
    """Shot phải nằm trong đúng một hiệp. Nếu id shot dùng chung giữa hai hiệp thì cặp dương lại
    vắt qua hai trận khác nhau — tệ hơn cả bug ban đầu."""
    from ai_core.data import load_manifest, save_manifest

    m1, _ = _manifest(tmp_path, [(200, 20, 20)] * 4, group="g00h1")
    m2, _ = _manifest(tmp_path, [(20, 200, 20)] * 4, group="g01h2")
    merged = tmp_path / "merged.json"
    save_manifest(merged, load_manifest(m1) + load_manifest(m2), meta={"fps": 1})

    out = tmp_path / "shots.json"
    _run(monkeypatch, merged, out, min_shot_frames=3)

    got = json.loads(out.read_text(encoding="utf-8"))["items"]
    halves_per_group: dict[str, set] = {}
    for i in got:
        halves_per_group.setdefault(i["group"], set()).add(i["extra"]["half"])
    assert all(len(v) == 1 for v in halves_per_group.values())
    assert {i["extra"]["half"] for i in got} == {"g00h1", "g01h2"}


def test_half_selection_covers_all_splits(tmp_path, monkeypatch):
    """Cắt theo max-frames phải XEN KẼ split, không theo thứ tự tên.

    Đã gặp thật: 10 hiệp đầu alphabet ra 9 train + 1 test + 0 val → early-stop không có val để
    chấm, mà không có gì báo lỗi. Ở đây train đứng trước theo tên nên cắt theo tên sẽ mất val/test.
    """
    from ai_core.data import load_manifest, save_manifest

    parts = []
    for name, split in [("a_tr1", "train"), ("b_tr2", "train"), ("c_tr3", "train"),
                        ("y_val1", "val"), ("z_te1", "test")]:
        m, _ = _manifest(tmp_path, [(200, 20, 20)] * 4, group=name, split=split)
        parts += load_manifest(m)
    merged = tmp_path / "all.json"
    save_manifest(merged, parts, meta={"fps": 1})

    out = tmp_path / "shots.json"
    _run(monkeypatch, merged, out, min_shot_frames=3, max_frames=20)

    got = json.loads(out.read_text(encoding="utf-8"))["items"]
    assert {i["split"] for i in got} == {"train", "val", "test"}    # không split nào bị rơi

    per_split: dict[str, int] = {}
    for i in got:
        per_split[i["split"]] = per_split.get(i["split"], 0) + 1
    # train phải chiếm phần lớn: xen kẽ 1:1:1 từng cho train chỉ 40% frame.
    assert per_split["train"] > per_split["val"]
    assert per_split["train"] > per_split["test"]


def test_empty_result_fails_loudly(tmp_path, monkeypatch):
    """Mọi shot đều quá ngắn → phải nổ, không ghi manifest rỗng cho bước train đọc.

    Guard theo split bắn trước guard tổng vì nó cụ thể hơn (nói rõ split nào rỗng). Điều test ở
    đây là *có nổ và không ghi file*, không phải câu chữ cụ thể.
    """
    m, _ = _manifest(tmp_path, [(200, 20, 20), (20, 20, 200), (220, 220, 30)])
    out = tmp_path / "shots.json"
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, m, out, min_shot_frames=3)
    assert "không lấy được frame nào" in str(e.value) or "Không giữ được frame nào" in str(e.value)
    assert not out.exists()
