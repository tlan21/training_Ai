"""WAV cụt không được để lại trên đĩa.

Dạng lỗi tệ nhất trong pipeline này: `build_highlight_features` cắt chuỗi về
`min(len(vision), len(audio))`, nên một WAV cụt chỉ làm hiệp đó ngắn đi vài trăm giây — vẫn train
được, vẫn ra F1, chỉ là trên dữ liệu thiếu. Không có gì báo.
"""

import pytest

from ai_core.scripts import extract_audio


def _setup(tmp_path, stem="g00h1"):
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / f"{stem}.mkv").write_bytes(b"khong phai video that")
    return videos, tmp_path / "out"


def _run(monkeypatch, videos, out):
    monkeypatch.setattr("sys.argv", ["extract_audio", "--videos", str(videos), "--out", str(out)])
    extract_audio.main()


def _fake_ffmpeg(n_bytes):
    """Giả ffmpeg: ghi file .tmp đúng kích thước yêu cầu."""
    def run(cmd, **kw):
        with open(cmd[-1], "wb") as f:
            f.write(b"\0" * n_bytes)
    return run


def test_full_size_wav_is_kept(tmp_path, monkeypatch):
    videos, out = _setup(tmp_path)
    monkeypatch.setattr("subprocess.run", _fake_ffmpeg(extract_audio._MIN_BYTES))
    _run(monkeypatch, videos, out)
    assert (out / "g00h1.wav").exists()
    assert not (out / "g00h1.wav.tmp").exists()


def test_short_wav_is_deleted_not_promoted(tmp_path, monkeypatch):
    videos, out = _setup(tmp_path)
    monkeypatch.setattr("subprocess.run", _fake_ffmpeg(1024))
    with pytest.raises(SystemExit):                     # không trích được gì → phải nổ
        _run(monkeypatch, videos, out)
    assert not (out / "g00h1.wav").exists()             # không đổi tên file cụt thành file thật
    assert not (out / "g00h1.wav.tmp").exists()         # cũng không để rác lại


def test_existing_full_wav_is_skipped(tmp_path, monkeypatch):
    """Chạy lại không được trích lại — 160 hiệp mất khá lâu."""
    videos, out = _setup(tmp_path)
    out.mkdir()
    (out / "g00h1.wav").write_bytes(b"\0" * extract_audio._MIN_BYTES)
    called = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: called.append(a))
    _run(monkeypatch, videos, out)
    assert called == []


def test_existing_short_wav_is_redone(tmp_path, monkeypatch):
    """File cụt sót lại từ lần bị cắt phải được trích lại, không được coi là 'đã có'."""
    videos, out = _setup(tmp_path)
    out.mkdir()
    (out / "g00h1.wav").write_bytes(b"\0" * 2048)
    monkeypatch.setattr("subprocess.run", _fake_ffmpeg(extract_audio._MIN_BYTES))
    _run(monkeypatch, videos, out)
    assert (out / "g00h1.wav").stat().st_size == extract_audio._MIN_BYTES


def test_no_videos_fails_loudly(tmp_path, monkeypatch):
    videos = tmp_path / "videos"
    videos.mkdir()
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, videos, tmp_path / "out")
    assert "Không có video nào" in str(e.value)
