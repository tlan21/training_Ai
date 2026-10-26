"""Prepare 30 unchanged VIVOS test utterances through real ASR -> News summary, with blank ratings."""

import csv
import hashlib
import html
import json
import random
import shutil
import subprocess
import time
import urllib.request
import wave
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIVOS = Path("D:/data_training_ai/data/raw/vivos/vivos")
OUT = ROOT / "data/processed/minigpt_human_pilot_20261015_v2"
API = "http://127.0.0.1:8001"
EXPECTED = "cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac"


def main():
    if (OUT / "samples.json").exists():
        raise SystemExit("Frozen pilot packet already exists; refusing to overwrite samples or human work")
    assert hashlib.sha256((ROOT / "ai-core/checkpoints/minigpt/best.pt").read_bytes()).hexdigest() == EXPECTED
    key = next(line.partition("=")[2].strip().strip('"\'') for line in (ROOT / ".env").read_text().splitlines()
               if line.strip().startswith("AI_SERVICE_KEY="))

    def request(path, data=None):
        req = urllib.request.Request(API + path, data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        with urllib.request.urlopen(req, timeout=180) as response:
            return json.load(response)

    health = request("/health")
    assert not health["stub_mode"] and not health["degraded"] and len(health["models_loaded"]) == 6
    refs = dict(line.strip().split(" ", 1) for line in (VIVOS / "test/prompts.txt").read_text(encoding="utf-8").splitlines() if line.strip())
    selected = random.Random(1337).sample(sorted((VIVOS / "test/waves").rglob("*.wav")), 30)
    assert len({p.stem for p in selected}) == 30
    (OUT / "audio").mkdir(parents=True, exist_ok=True)
    for i, path in enumerate(selected, 1):
        shutil.copy2(path, OUT / "audio" / f"sample_{i:02}.wav")
    subprocess.run(["docker", "compose", "--env-file", ".env", "-f", "docker-compose.yml", "exec", "-T", "inference-service",
                    "mkdir", "-p", "/tmp/minigpt-human-pilot"], cwd=ROOT, check=True)
    subprocess.run(["docker", "compose", "--env-file", ".env", "-f", "docker-compose.yml", "cp", str(OUT / "audio") + "/.",
                    "inference-service:/tmp/minigpt-human-pilot/"], cwd=ROOT, check=True)
    rows = []
    for i, path in enumerate(selected, 1):
        started = time.monotonic()
        asr = request("/v1/asr/completions", {"audio_url": f"/tmp/minigpt-human-pilot/sample_{i:02}.wav", "language": "vi"})
        summary = request("/v1/completions", {"prompt": asr["full_transcript"], "max_tokens": 96, "temperature": 0})
        with wave.open(str(path)) as audio:
            duration = audio.getnframes() / audio.getframerate()
        rows.append({"sample_id": f"sample_{i:02}", "source_id": path.stem, "speaker": path.parent.name,
                     "audio": f"audio/sample_{i:02}.wav", "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "duration_seconds": duration, "reference": refs[path.stem], "asr": asr,
                     "summary": summary["choices"][0]["text"], "request_temperature": 0,
                     "elapsed_seconds": time.monotonic() - started})
        (OUT / "samples.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{i}/30 {path.stem}: real ASR chars={len(asr['full_transcript'])}, summary chars={len(rows[-1]['summary'])}", flush=True)
    for rater in range(1, 4):
        path = OUT / f"ratings_rater_{rater}.csv"
        if not path.exists():
            with path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["sample_id", "overall_score_1_to_5", "notes"])
                writer.writerows((r["sample_id"], "", "") for r in rows)
    shutil.copy2(VIVOS / "COPYING", OUT / "VIVOS_LICENSE.txt")
    shutil.copy2(VIVOS / "README", OUT / "VIVOS_README.txt")
    instructions = """# Bộ chấm thử Mini-GPT trên ASR thật — VIVOS

30 utterance nguyên gốc VIVOS test, seed1337, không ghép câu/không chọn lại theo output.
Đây là pilot giọng đọc ngắn, KHÔNG đại diện30 video thực tế hoặc thay full video human evaluation.
Audio: AILAB, VNUHCM University of Science, VIVOS v1.00 (2016), CC BY-NC-SA4.0; xem LICENSE/README đi kèm.

Mỗi người dùng file ratings_rater_N.csv riêng, chấm độc lập tất cả30 mẫu, không xem điểm nhau.
Mở review.html, nghe audio, đối chiếu câu gốc/ASR/summary. Chấm chất lượng summary so với điều thực sự được nói,
bao gồm lỗi dây chuyền ASR; không suy điểm từ ROUGE. Không dùng model khác để chấm thay người.

1: sai ý hoặc không có output;2: sai nhiều, hầu như phải viết lại;3: nắm được ý chính nhưng cần sửa đáng kể;
4: đúng ý, chỉ cần chỉnh nhẹ;5: chính xác, gọn, rõ và không thêm thông tin không có trong audio.

Điền overall_score_1_to_5 bằng số nguyên1–5, notes tùy chọn; không đổi sample_id.
Chỉ tổng hợp khi đủ90 điểm thật (30×3): mean≥3/5 là ngưỡng đã chốt; báo thêm mean từng người/từng mẫu.
Tất cả điểm hiện để TRỐNG. Pilot này không chứng minh full DoD cho video.
Đặt3 CSV đã điền trở lại thư mục chứa review.html trong dự án rồi chạy từ E:/traning_ai:
ai-core/.venv/Scripts/python.exe dist/kaggle/kernel-minigpt-news/score_human_pilot.py
"""
    (OUT / "README.md").write_text(instructions, encoding="utf-8")
    cards = []
    for row in rows:
        esc = html.escape
        cards.append(f'<article><h2>{row["sample_id"]}</h2><audio controls preload="none" src="{row["audio"]}"></audio>'
                     f'<p><b>Câu gốc:</b> {esc(row["reference"])}</p><p><b>ASR thật:</b> {esc(row["asr"]["full_transcript"])}</p>'
                     f'<p><b>Summary:</b> {esc(row["summary"])}</p></article>')
    (OUT / "review.html").write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Chấm thử ASR → summary</title>'
                                   '<style>body{font:17px system-ui;max-width:900px;margin:32px auto;padding:16px}article{border-top:1px solid #bbb;padding:20px 0}p{line-height:1.5}audio{width:100%}</style>'
                                   '<h1>Bộ chấm thử30 mẫu ASR thật</h1><p>VIVOS giọng đọc ngắn; chưa đại diện video thực tế. Xem README.md; chấm độc lập trong3 CSV, mọi điểm đang trống.</p>'
                                   + ''.join(cards) + '</html>', encoding="utf-8")
    assert len(rows) == 30 and all((OUT / row["audio"]).is_file() for row in rows)
    for i in range(1, 4):
        with (OUT / f"ratings_rater_{i}.csv").open(encoding="utf-8-sig") as f:
            ratings = list(csv.DictReader(f))
        assert len(ratings) == 30 and [r["sample_id"] for r in ratings] == [r["sample_id"] for r in rows]
    manifest = {"date": "2026-10-15", "status": "PILOT READY — HUMAN RATINGS PENDING", "seed": 1337,
                "source": str(VIVOS / "test"), "license": "CC BY-NC-SA 4.0 / AILAB VNUHCM University of Science",
                "samples": 30, "speakers": len({r["speaker"] for r in rows}), "duration_seconds": sum(r["duration_seconds"] for r in rows),
                "checkpoint_sha256": EXPECTED, "asr_checkpoint_sha256": hashlib.sha256((ROOT / "ai-core/checkpoints/asr_ctc/best.pt").read_bytes()).hexdigest(),
                "format": "sum; actual uppercase CTC lowercased by service; EOS512/96; greedy", "packet": str(OUT),
                "human_ratings": "UNMEASURED — blank sheets supplied; never automatically assigned",
                "samples_sha256": hashlib.sha256((OUT / "samples.json").read_bytes()).hexdigest(),
                "limitation": "Short read utterances, not real-world videos; cannot certify video human DoD",
                "empty_asr": sum(not r["asr"]["full_transcript"] for r in rows), "empty_summary": sum(not r["summary"] for r in rows)}
    (ROOT / "data/manifests/minigpt_human_pilot.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    with zipfile.ZipFile(OUT.with_suffix(".zip"), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in OUT.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(OUT))
    print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
