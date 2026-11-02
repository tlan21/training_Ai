"""Run Claude's unchanged parity.py with HTTP inside the existing AI container.

Usage (Claude venv, cwd=Claude worktree): runner.py container features.pt output.json
No host port, new container, checkpoint copy, or AI source change is needed.
"""
import io
import json
import pathlib
import subprocess
import sys
import urllib.request

container, features, output = sys.argv[1:4]
base = "http://127.0.0.1:8001"
real_urlopen = urllib.request.urlopen


def container_urlopen(request, timeout=600):
    if not isinstance(request, urllib.request.Request) or not request.full_url.startswith(base + "/"):
        return real_urlopen(request, timeout=timeout)
    payload = {
        "url": request.full_url,
        "body": request.data.decode(),
        "headers": dict(request.header_items()),
    }
    code = """import json,sys,urllib.request
p=json.load(sys.stdin)
r=urllib.request.Request(p['url'],data=p['body'].encode(),headers=p['headers'],method='POST')
with urllib.request.urlopen(r,timeout=600) as response:
    print(response.read().decode())
"""
    response = subprocess.run(
        ["docker", "exec", "-i", container, "python", "-c", code],
        input=json.dumps(payload), capture_output=True, text=True,
        encoding="utf-8", timeout=timeout + 30, check=True,
    )
    json.loads(response.stdout)
    return io.BytesIO(response.stdout.encode())


urllib.request.urlopen = container_urlopen
source = subprocess.check_output(
    ["git", "show", "479f5d5:coordination/claude/evidence/AI-22_2026-11-02/parity.py"],
    text=True, encoding="utf-8",
)
sys.argv = ["Claude parity.py", container, base, features, output]
exec(compile(source, "Claude parity.py at master479f5d5", "exec"), {"__name__": "__main__"})
assert json.loads(pathlib.Path(output).read_text(encoding="utf-8"))["PASS"] is True
