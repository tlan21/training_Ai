"""Hai bất biến của bước ghép feature, cả hai đều đã hỏng thật ở T1.5.

1. Hiệp có dữ liệu hỏng phải bị LOẠI, không được thành mẫu 1 giây. 5 hiệp SoccerNet 224p có stream
   vorbis rỗng (~6 KB packet, hiệp tốt 33 MB); ffmpeg vẫn exit 0, WAV ra 4 KB, feature còn 1 giây,
   `HighlightWindowDataset` vẫn sinh một cửa sổ toàn 0 + nhãn IGNORE. g18h1/g18h2 lọt vào VAL của
   vòng 1 và vòng 2 đúng kiểu đó — val 6 hiệp thực chất chỉ 4 hiệp dùng được.
2. Split phải bốc ở mức TRẬN. Manifest chia theo hiệp nên hiệp 1 và hiệp 2 cùng trận rơi vào hai
   tập khác nhau; đo được mức thổi phồng là ~0,15 điểm F1 (0.2818 khi rò rỉ vs 0.1297 khi sạch).

Fixture dùng 12 trận vì `split_by_group` chia 80/10/10: dưới 10 trận thì `int(0.1 * n)` ra 0 và
val/test rỗng — script bắn SystemExit đúng như thiết kế, nhưng test thì thành vô nghĩa.
Dùng hiệp 100 giây + `--min-seconds 60` để mỗi test chạy trong vài giây thay vì cả phút.
"""

import json

import pytest
import torch

N_SEC = 100
MIN_SEC = 60
_ALL = {f"g{i:02d}h{h}": "train" for i in range(12) for h in (1, 2)}


def _build(tmp_path, halves, n_sec=N_SEC, broken=(), silent=()):
    """halves: {stem: split}. `broken` = WAV cụt (1 giây). `silent` = WAV đủ dài nhưng toàn số 0.

    WAV mặc định phải CÓ TÍN HIỆU. Bản trước ghi `torch.zeros` cho mọi hiệp, nên cả suite xanh
    trong khi 100% audio là khoảng lặng — đúng điểm mù mà chốt `_MIN_VOICED` sinh ra để bịt.
    """
    import soundfile as sf

    from ai_core.data import ManifestItem, save_manifest

    (tmp_path / "wav").mkdir()
    (tmp_path / "lab").mkdir()
    vision, items = {}, []
    torch.manual_seed(0)
    for stem, split in halves.items():
        vision[stem] = torch.randn(n_sec, 4)
        n_samples = 16000 if stem in broken else 16000 * n_sec
        sig = torch.zeros(n_samples) if stem in silent else torch.randn(n_samples) * 0.1
        sf.write(tmp_path / "wav" / f"{stem}.wav", sig.numpy(), 16000)
        (tmp_path / "lab" / f"{stem}.json").write_text(
            json.dumps({"labels": [0] * n_sec, "meta": {}}), encoding="utf-8")
        items.append(ManifestItem(path=f"{stem}.png", label="bong_da", split=split,
                                  group=stem, extra={"sec": 0}))
    torch.save(vision, tmp_path / "vision.pt")
    save_manifest(tmp_path / "man.json", items, meta={"fps": 1})
    return tmp_path / "out.pt"


def _run(monkeypatch, tmp_path, out, min_seconds=MIN_SEC):
    from ai_core.scripts import build_highlight_features

    monkeypatch.setattr("sys.argv", [
        "build_highlight_features", "--audio", str(tmp_path / "wav"),
        "--vision", str(tmp_path / "vision.pt"), "--labels", str(tmp_path / "lab"),
        "--manifest", str(tmp_path / "man.json"), "--out", str(out),
        "--min-seconds", str(min_seconds)])
    build_highlight_features.main()
    return torch.load(out, map_location="cpu", weights_only=False)


def _match_of(name):
    return name[:3]


def test_half_with_empty_audio_is_dropped_not_kept_as_one_second(tmp_path, monkeypatch):
    raw = _run(monkeypatch, tmp_path, _build(tmp_path, _ALL, broken=("g00h2", "g05h1")))

    kept = {d["name"] for s in raw for d in raw[s]}
    assert "g00h2" not in kept and "g05h1" not in kept
    assert len(kept) == len(_ALL) - 2
    assert all(d["vision"].shape[0] >= MIN_SEC for s in raw for d in raw[s])


def test_half_with_long_but_silent_audio_is_dropped(tmp_path, monkeypatch):
    """WAV ĐỦ DÀI mà không có tiếng cũng phải bị loại — `--min-seconds` không bắt được ca này.

    5 hiệp SoccerNet 224p có stream vorbis rỗng may mắn cho ra WAV 4 KB nên rơi dưới ngưỡng giây.
    Đổi một cờ ffmpeg (`aresample=async=1` độn im lặng cho khớp timestamp) là ra file 85 MB / 2620
    giây qua sạch mọi chốt, rồi nhánh audio học trên khoảng trắng gắn nhãn highlight. Hiệp lành
    thấp nhất trong 155 hiệp thật có 99,74% số giây vượt ngưỡng, hiệp rỗng có 0,19%.
    """
    raw = _run(monkeypatch, tmp_path, _build(tmp_path, _ALL, silent=("g03h1", "g07h2")))

    kept = {d["name"] for s in raw for d in raw[s]}
    assert "g03h1" not in kept and "g07h2" not in kept
    assert len(kept) == len(_ALL) - 2
    for s in raw:                                  # hiệp giữ lại phải thật sự có tiếng
        for d in raw[s]:
            assert (d["audio"][:, 0] > 1e-3).float().mean() > 0.5, d["name"]


def test_both_halves_of_a_match_land_in_the_same_split(tmp_path, monkeypatch):
    """Manifest cố tình cho hai hiệp cùng trận khác split — cột split của manifest phải bị bỏ qua
    hoàn toàn, nếu không hiệp anh em rò rỉ sang test."""
    halves = dict(_ALL)
    halves["g00h1"], halves["g00h2"] = "train", "test"
    halves["g01h1"], halves["g01h2"] = "test", "val"
    raw = _run(monkeypatch, tmp_path, _build(tmp_path, halves))

    where = {d["name"]: s for s in raw for d in raw[s]}
    for i in range(12):
        assert where[f"g{i:02d}h1"] == where[f"g{i:02d}h2"]
    per = {s: {_match_of(d["name"]) for d in raw[s]} for s in raw}
    assert not (per["train"] & per["test"])
    assert not (per["val"] & per["test"])
    assert not (per["train"] & per["val"])


def test_split_is_deterministic_for_a_given_seed(tmp_path, monkeypatch):
    """Chạy lại phải ra đúng tập test cũ — evaluation_plan §0.2 đòi test cố định."""
    first = _run(monkeypatch, tmp_path, _build(tmp_path, _ALL))
    names = {s: sorted(d["name"] for d in first[s]) for s in first}

    again = tmp_path / "again"
    again.mkdir()
    second = _run(monkeypatch, again, _build(again, _ALL))
    assert {s: sorted(d["name"] for d in second[s]) for s in second} == names


def test_empty_split_fails_loudly(tmp_path, monkeypatch):
    """Loại hết vì ngưỡng quá cao → phải nổ. Split rỗng thì Trainer._evaluate trả None và
    early-stop im lặng vô hiệu (đã cắn ở T1.3c)."""
    out = _build(tmp_path, _ALL)
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, tmp_path, out, min_seconds=10_000)
    assert "rỗng" in str(e.value)


def test_lengths_are_aligned_across_vision_audio_labels(tmp_path, monkeypatch):
    raw = _run(monkeypatch, tmp_path, _build(tmp_path, _ALL))
    for split in raw:
        for d in raw[split]:
            assert d["vision"].shape[0] == d["audio"].shape[0] == d["labels"].shape[0]
