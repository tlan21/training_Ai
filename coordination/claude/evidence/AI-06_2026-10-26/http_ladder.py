"""AI-06: gọi HTTP thật từng endpoint, Bearer từ inference-service/.env, validate bằng app.schemas. Lưu response ra responses/."""
import base64, json, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path("E:/traning_ai")
OUT = Path("D:/tmp/ai06_20261026")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
sys.path[:0] = [str(ROOT / "inference-service"), str(ROOT / "ai-core")]
from app import schemas  # noqa: E402

KEY = next(l.split("=", 1)[1].strip() for l in (ROOT / "inference-service/.env").read_text(encoding="utf-8").splitlines()
           if l.startswith("AI_SERVICE_KEY="))
(OUT / "responses").mkdir(exist_ok=True)


def call(name, method, path, body=None, auth=KEY):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {auth}"} if auth else {})})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            code, data = r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        code, data = e.code, json.loads(e.read() or b"{}")
    ms = round((time.perf_counter() - t) * 1000)
    (OUT / "responses" / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return code, data, ms


rows = []
def record(name, code, ms, ok, note):
    rows.append((name, code, ms, "PASS" if ok else "FAIL", note))
    print(f"{name:<22} HTTP {code} {ms:>6} ms  {'PASS' if ok else 'FAIL'}  {note}", flush=True)

c, d, ms = call("health", "GET", "/health", auth=None)
h = schemas.HealthResponse.model_validate(d)
record("health", c, ms, c == 200 and not h.stub_mode and len(h.models_loaded) == 6 and not h.degraded,
       f"stub_mode={h.stub_mode} models={h.models_loaded} degraded={h.degraded} device={h.device}")

for name, auth in (("no_bearer", None), ("wrong_bearer", "sk-local-wrong")):
    c, d, ms = call(name, "POST", "/v1/completions", {"prompt": "x", "max_tokens": 1}, auth=auth)
    record(name, c, ms, c == 401 and d.get("error", {}).get("code") == "UNAUTHORIZED", json.dumps(d, ensure_ascii=False))

frames = sorted(str(p).replace("\\", "/") for p in (OUT / "frames").glob("*.jpg"))
c, d, ms = call("vision", "POST", "/v1/vision/completions", {"keyframes": frames})
ok = c == 200
if ok:
    v = schemas.VisionResponse.model_validate(d)
    ok = v.category_suggestion in {"bong_da", "the_thao", "ca_nhac", "tin_tuc"} and len(v.embeddings_256) == len(frames) \
        and all(len(e) == 256 for e in v.embeddings_256)
record("vision", c, ms, ok, f"frames={len(frames)} category={d.get('category_suggestion')} emb={len(d.get('embeddings_256', []))}x{len((d.get('embeddings_256') or [[]])[0])}")

c, d, ms = call("asr", "POST", "/v1/asr/completions", {"audio_url": str(OUT / "clip10s.wav").replace("\\", "/"), "language": "vi"})
ok = c == 200 and schemas.ASRResponse.model_validate(d) is not None
record("asr", c, ms, ok, f"segments={len(d.get('segments', []))} transcript={d.get('full_transcript', '')[:80]!r}")

import torch, wave  # noqa: E401,E402
from ai_core.audio.features import audio_features_per_second  # noqa: E402
with wave.open(str(OUT / "clip10s.wav")) as w:
    pcm = torch.frombuffer(bytearray(w.readframes(w.getnframes())), dtype=torch.int16).float() / 32768
audio = audio_features_per_second(pcm, 16000)[: len(frames)].tolist()
vis = json.loads((OUT / "responses/vision.json").read_text(encoding="utf-8")).get("embeddings_256", [])[: len(audio)]
c, d, ms = call("highlight", "POST", "/v1/highlight/completions",
                {"video_id": "vid_ai06probe", "features": {"vision_embeddings": vis, "audio_spectrogram_features": audio}})
ok = c == 200
if ok:
    hr = schemas.HighlightResponse.model_validate(d)
    ok = len(hr.timeline_scores) == len(vis) and all(0 <= s.score <= 100 for s in hr.timeline_scores)
record("highlight", c, ms, ok, f"seconds={len(vis)} audio_dim={len(audio[0]) if audio else 0} scores={[round(s['score'],1) for s in d.get('timeline_scores', [])]}")

prompt = ("Tóm tắt: Chiều nay tại Hà Nội, đội tuyển bóng đá quốc gia đã có buổi tập đầu tiên chuẩn bị cho vòng loại. "
          "Huấn luyện viên cho biết toàn đội đang trong trạng thái tốt và quyết tâm giành chiến thắng.")
c, d, ms = call("completions", "POST", "/v1/completions", {"prompt": prompt, "max_tokens": 48, "temperature": 0})
ok = c == 200 and schemas.CompletionResponse.model_validate(d) is not None and bool(d["choices"][0]["text"].strip())
record("completions", c, ms, ok, f"usage={d.get('usage')} text={(d.get('choices') or [{}])[0].get('text', '')[:80]!r}")

img = "data:image/jpeg;base64," + base64.b64encode(Path(frames[0]).read_bytes()).decode()
c, d, ms = call("search", "POST", "/v1/search/completions", {"image": img, "top_k": 5, "threshold": 0.75})
record("search", c, ms, c == 503 and d.get("error", {}).get("code") == "AI_UNAVAILABLE", "expect 503 AI_UNAVAILABLE (Milvus off): " + json.dumps(d, ensure_ascii=False)[:160])

c, d, ms = call("recommendation", "POST", "/v1/recommendation/completions", {"user_id": "usr_ai06probe", "limit": 5, "context": {}})
record("recommendation", c, ms, c == 503 and d.get("error", {}).get("code") == "AI_UNAVAILABLE", "expect 503 AI_UNAVAILABLE (Milvus off): " + json.dumps(d, ensure_ascii=False)[:160])

(OUT / "ladder_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("SUMMARY", sum(r[3] == "PASS" for r in rows), "/", len(rows), "PASS")
