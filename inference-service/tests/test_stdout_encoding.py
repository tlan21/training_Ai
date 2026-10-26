"""AI-07: Vietnamese log lines must not crash a handler when stdout is redirected with a non-UTF-8 code page (Windows cp1252)."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vietnamese_log_survives_redirected_stdout():
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT.parent / "ai-core")])
    code = ("from app import services; services.settings.force_stub = True; "
            "services._warn('search/milvus', 'siamese', RuntimeError('lỗi kết nối → thử lại'))")
    proc = subprocess.run([sys.executable, "-X", "utf8=0", "-c", code], cwd=ROOT, env=env, capture_output=True)
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    assert "lỗi kết nối" in proc.stdout.decode("utf-8")
