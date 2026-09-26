from ai_core.scripts.fetch_soccernet_videos import games_missing_video


def test_missing_video_skips_games_already_processed(tmp_path):
    """Video trận cũ bị xoá để lấy chỗ đĩa: không có `skip` thì lô sau tải lại chính trận cũ."""
    for game in ("a", "b", "c"):
        d = tmp_path / "lg" / "2015" / game
        d.mkdir(parents=True)
        (d / "Labels-v2.json").write_text("{}")
    for h in ("1_224p.mkv", "2_224p.mkv"):
        (tmp_path / "lg" / "2015" / "c" / h).write_bytes(b"x")

    assert games_missing_video(str(tmp_path)) == ["lg/2015/a", "lg/2015/b"]
    assert games_missing_video(str(tmp_path), {"lg/2015/a"}) == ["lg/2015/b"]
