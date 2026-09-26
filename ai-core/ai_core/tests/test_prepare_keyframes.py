"""T1.2a phải chịu được video hỏng — dataset_spec §3.1 lấy nguồn mở nên file hỏng là chắc chắn có.

Lô thử đầu tiên (12 video Wikimedia Commons) có 4 file Decord không đọc nổi. Bản đầu của script để
exception nổ lên → mất cả lô vì đúng 1 file. Bản hiện tại bỏ qua file hỏng (có ffmpeg đỡ trước), và
QUAN TRỌNG HƠN là báo lỗi to nếu KHÔNG trích được gì: manifest rỗng mà exit 0 thì bước train sau
chạy trên 0 mẫu, "hội tụ" ngay, mất hàng giờ mới lần ra nguyên nhân.
"""

import json

import pytest


def _run_main(monkeypatch, videos, labels, out, manifest):
    from ai_core.scripts import prepare_keyframes

    monkeypatch.setattr("sys.argv", [
        "prepare_keyframes", "--videos", str(videos), "--labels", str(labels),
        "--out", str(out), "--manifest", str(manifest),
    ])
    prepare_keyframes.main()


def test_all_videos_unreadable_fails_loudly_instead_of_empty_manifest(tmp_path, monkeypatch):
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "broken.webm").write_bytes(b"\x00 khong phai video \xff" * 64)
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"broken": "bong_da"}), encoding="utf-8")
    manifest = tmp_path / "manifests" / "vit.json"

    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, videos, labels, tmp_path / "keyframes", manifest)

    assert "Không trích được keyframe nào" in str(exc.value)
    assert not manifest.exists()          # không được để lại manifest rỗng cho bước sau đọc


def _fake_half(tmp_path, stem="g00h1", n=3, done=True):
    """Dựng sẵn một hiệp 'đã trích xong' để chấm nhánh nối lại."""
    from PIL import Image

    videos = tmp_path / "videos"
    videos.mkdir(exist_ok=True)
    (videos / f"{stem}.mkv").write_bytes(b"khong phai video that")
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({stem: "bong_da"}), encoding="utf-8")

    d = tmp_path / "kf" / stem
    d.mkdir(parents=True)
    for sec in range(n):
        Image.new("RGB", (8, 6), (30, 90, 200)).save(d / f"{stem}_s{sec:05d}.png")
    if done:
        (d / ".done").write_text("")
    return videos, labels


def test_finished_half_is_reused_without_re_extracting(tmp_path, monkeypatch):
    """Có mốc .done → dùng lại PNG sẵn có, KHÔNG gọi lại bộ trích. 160 hiệp mất nhiều giờ nên chạy
    lại sau khi bị cắt không được làm lại từ đầu."""
    from ai_core.scripts import prepare_keyframes

    videos, labels = _fake_half(tmp_path, n=3)
    called = []
    monkeypatch.setattr(prepare_keyframes, "extract_keyframes_1fps",
                        lambda *a, **k: called.append(a) or [])
    manifest = tmp_path / "m.json"
    _run_main(monkeypatch, videos, labels, tmp_path / "kf", manifest)

    assert called == []                                        # không trích lại
    items = json.loads(manifest.read_text(encoding="utf-8"))["items"]
    assert len(items) == 3
    assert {i["extra"]["sec"] for i in items} == {0, 1, 2}


def test_reuse_manifest_bo_qua_hash_nhung_khong_dung_lai_khi_png_moi(tmp_path, monkeypatch):
    """`--reuse-manifest` phải bỏ hash cho PNG không đổi, và PHẢI hash lại PNG ghi sau manifest.

    Nhánh [có sẵn] hash SHA-1 toàn bộ từng PNG. Đo thật: 25 giây/hiệp, 160 hiệp = ~67 phút chỉ để
    dựng lại manifest cho hiệp không cần làm gì, và chi phí tăng theo lô. Nhưng dùng lại checksum
    chỉ theo đường dẫn thì sai: PNG được trích lại vẫn mang checksum cũ, manifest khẳng định dữ liệu
    là một thứ trong khi trên đĩa là thứ khác — sai lệch không có gì báo.
    """
    import os
    import time

    from ai_core.data import file_checksum
    from ai_core.scripts import prepare_keyframes

    videos, labels = _fake_half(tmp_path, n=3)
    monkeypatch.setattr(prepare_keyframes, "extract_keyframes_1fps", lambda *a, **k: [])

    old = tmp_path / "old.json"
    _run_main(monkeypatch, videos, labels, tmp_path / "kf", old)
    before = {i["path"]: i["extra"]["checksum"]
              for i in json.loads(old.read_text(encoding="utf-8"))["items"]}
    assert len(before) == 3

    # Đổi nội dung ĐÚNG MỘT PNG và đẩy mtime vượt manifest → checksum của nó không được dùng lại.
    pngs = sorted(before)
    with open(pngs[0], "wb") as f:
        f.write(b"noi dung khac hoan toan")
    future = time.time() + 5
    os.utime(pngs[0], (future, future))

    hashed = []
    real = prepare_keyframes.file_checksum
    monkeypatch.setattr(prepare_keyframes, "file_checksum",
                        lambda p, *a, **k: (hashed.append(p), real(p, *a, **k))[1])
    monkeypatch.setattr("sys.argv", [
        "prepare_keyframes", "--videos", str(videos), "--labels", str(labels),
        "--out", str(tmp_path / "kf"), "--manifest", str(tmp_path / "new.json"),
        "--reuse-manifest", str(old),
    ])
    prepare_keyframes.main()

    assert hashed == [pngs[0]], f"chỉ được hash lại PNG đã đổi, đã hash: {hashed}"
    after = {i["path"]: i["extra"]["checksum"]
             for i in json.loads((tmp_path / "new.json").read_text(encoding="utf-8"))["items"]}
    assert after[pngs[0]] == file_checksum(pngs[0]) != before[pngs[0]]   # đã cập nhật
    assert all(after[p] == before[p] for p in pngs[1:])                  # còn lại dùng lại


def test_half_without_done_marker_is_extracted_again(tmp_path, monkeypatch):
    """Thiếu mốc .done = lần trước bị cắt giữa đường → phải trích lại, không tin số PNG có sẵn."""
    from ai_core.scripts import prepare_keyframes

    videos, labels = _fake_half(tmp_path, n=2, done=False)
    called = []

    def fake_extract(video_path, out_dir):
        called.append(video_path)
        raise RuntimeError("decord nga")          # đẩy sang nhánh ffmpeg rồi 'không đọc được'

    monkeypatch.setattr(prepare_keyframes, "extract_keyframes_1fps", fake_extract)
    with pytest.raises(SystemExit):               # không còn hiệp hợp lệ nào
        _run_main(monkeypatch, videos, labels, tmp_path / "kf", tmp_path / "m.json")
    assert len(called) == 1


def test_videos_without_label_are_skipped_not_fatal(tmp_path, monkeypatch):
    """Video không có trong labels.json chỉ bị bỏ qua, không ném lỗi lạ; nhưng vì không còn video
    hợp lệ nào nên vẫn phải kết thúc bằng SystemExit — không im lặng tạo manifest rỗng."""
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "khong_co_nhan.webm").write_bytes(b"rac")
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"video_khac": "bong_da"}), encoding="utf-8")

    with pytest.raises(SystemExit):
        _run_main(monkeypatch, videos, labels, tmp_path / "kf", tmp_path / "m.json")


def test_finished_half_stays_in_manifest_after_its_video_is_deleted(tmp_path, monkeypatch):
    """Video trận cũ bị xoá để lấy chỗ đĩa: hiệp đã có .done vẫn phải vào manifest. Mất nó thì
    build_highlight_features bốc split chỉ trên hiệp mới và gán hiệp cũ vào 'train' không báo gì."""
    from ai_core.scripts import prepare_keyframes

    videos, labels = _fake_half(tmp_path, n=3)
    (videos / "g00h1.mkv").unlink()
    (videos / "g01h1.mkv").write_bytes(b"video moi")
    labels.write_text(json.dumps({"g00h1": "bong_da", "g01h1": "bong_da"}), encoding="utf-8")

    def fake_extract(video_path, out_dir):
        from PIL import Image
        import os
        os.makedirs(out_dir, exist_ok=True)
        p = os.path.join(out_dir, "g01h1_s00000.png")
        Image.new("RGB", (8, 6)).save(p)
        return [p]

    monkeypatch.setattr(prepare_keyframes, "extract_keyframes_1fps", fake_extract)
    manifest = tmp_path / "m.json"
    _run_main(monkeypatch, videos, labels, tmp_path / "kf", manifest)

    items = json.loads(manifest.read_text(encoding="utf-8"))["items"]
    assert {i["group"] for i in items} == {"g00h1", "g01h1"}
    assert sum(i["group"] == "g00h1" for i in items) == 3
