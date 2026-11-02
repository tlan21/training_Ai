"""AI-19: build the human labelling page for news highlights from proposals.json (CLAUDE_PROPOSED → human edits → HUMAN_VERIFIED export).

  python dist/kaggle/kernel-fusion-r8/build_label_page.py D:/data_training_ai/highlight_news_v1 ../minigpt_real_video_20261015/raw/youtube
Writes <out>/label_news.html (open by double-click; videos load from the relative raw path; progress kept in localStorage).
"""
import json
import sys
from pathlib import Path

PAGE = r"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Gán nhãn highlight — tin tức (AI-19)</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;display:flex;height:100vh;color:#222}
#list{width:250px;overflow:auto;border-right:1px solid #ddd;padding:8px;font-size:14px}
#list div{padding:6px;border-radius:6px;cursor:pointer}#list div.on{background:#e8f0fe}#list .ok{color:#188038}
#main{flex:1;overflow:auto;padding:12px}video{width:100%;max-height:52vh;background:#000}
canvas{width:100%;height:70px;cursor:pointer;border:1px solid #ccc;margin-top:6px}
table{border-collapse:collapse;margin-top:8px}td,th{padding:4px 6px;border-bottom:1px solid #eee;font-size:14px}
input[type=number]{width:90px}button{margin:2px}.guide{background:#fff8e1;padding:8px;border-radius:6px;font-size:13px}
.prop{color:#9a6700;font-size:12px}
</style></head><body>
<div id="list"></div>
<div id="main">
 <div class="guide"><b>Highlight (tin tức) = đoạn đáng xem nhất nếu chỉ được xem vài đoạn ngắn:</b> tin chính/tin nóng, phát biểu hoặc số liệu quan trọng,
 hình ảnh hiện trường nổi bật. Không chọn: giới thiệu chương trình, chuyển cảnh, quảng cáo, đoạn đọc lại. Đoạn nên dài 5–60 giây.
 __AIHINT__ Video không có đoạn nào đáng xem: xóa hết rồi tick "Đã duyệt".
 Chỉ video đã tick mới được xuất (HUMAN_VERIFIED).</div>
 <h3 id="title"></h3><video id="v" controls preload="metadata"></video>
 <canvas id="c" width="1600" height="70" title="Điểm AI theo giây (vạch đỏ = ngưỡng cắt). Click để tua."></canvas>
 <div><button onclick="addSeg()">+ Thêm đoạn tại vị trí đang xem (10 s)</button>
  <label><input type="checkbox" id="rev" onchange="setRev(this.checked)"> <b>Đã duyệt video này</b></label>
  &nbsp; Ghi chú: <input id="note" size="40" oninput="cur().note=this.value;save()"></div>
 <table><thead><tr><th>#</th><th>Bắt đầu (s)</th><th></th><th>Kết thúc (s)</th><th></th><th>Dài</th><th>Nguồn</th><th></th></tr></thead><tbody id="segs"></tbody></table>
 <p>Người duyệt: <input id="rater" placeholder="tên" oninput="state.rater=this.value;save()"> <button onclick="exportJson()">Xuất file nhãn (JSON)</button> <span id="msg"></span></p>
</div>
<script>
const DATA = __DATA__, RAW = __RAW__, KEY = __KEY__;
let state = JSON.parse(localStorage.getItem(KEY) || "null") || {rater: "", videos: {}};
for (const [id, p] of Object.entries(DATA.videos)) if (!state.videos[id])
  state.videos[id] = {reviewed: false, note: "", segments: p.segments.map(s => ({start: s.start, end: s.end, origin: "CLAUDE_PROPOSED"}))};
let curId = Object.keys(DATA.videos)[0];
const $ = id => document.getElementById(id), cur = () => state.videos[curId], v = $("v");
function save() { localStorage.setItem(KEY, JSON.stringify(state)); }
function list() {
  $("list").innerHTML = Object.keys(DATA.videos).map((id, i) => {
    const s = state.videos[id], p = DATA.videos[id];
    return '<div class="' + (id === curId ? "on" : "") + '" data-id="' + id + '">' + (i + 1) + ". " + id +
      ' <span class="' + (s.reviewed ? "ok" : "") + '">' + (s.reviewed ? "✓ đã duyệt" : "chưa duyệt") + "</span><br><small>" +
      Math.round(p.duration / 60) + " phút · " + p.category + " · " + s.segments.length + " đoạn</small></div>";
  }).join("");
  for (const el of $("list").children) el.onclick = () => pick(el.dataset.id);
}
function pick(id) { curId = id; v.src = RAW + "/" + id + ".mp4"; render(); }
function row(s, i) {
  return "<tr><td>" + (i + 1) + '</td><td><input type="number" step="0.1" value="' + s.start + '" data-i="' + i + '" data-k="start"></td>' +
    '<td><button data-now="' + i + '" data-k="start">⟵ hiện tại</button><button data-play="' + i + '">▶</button></td>' +
    '<td><input type="number" step="0.1" value="' + s.end + '" data-i="' + i + '" data-k="end"></td>' +
    '<td><button data-now="' + i + '" data-k="end">⟵ hiện tại</button></td><td>' + (s.end - s.start).toFixed(1) + " s</td>" +
    '<td class="prop">' + (s.origin === "CLAUDE_PROPOSED" ? "AI đề xuất" : "người") + '</td><td><button data-del="' + i + '">Xóa</button></td></tr>';
}
function render() {
  $("title").textContent = curId; $("rev").checked = cur().reviewed; $("note").value = cur().note || ""; $("rater").value = state.rater || "";
  cur().segments.sort((a, b) => a.start - b.start);
  $("segs").innerHTML = cur().segments.map(row).join("");
  for (const el of $("segs").querySelectorAll("input")) el.onchange = () => edit(+el.dataset.i, el.dataset.k, el.value);
  for (const el of $("segs").querySelectorAll("[data-now]")) el.onclick = () => edit(+el.dataset.now, el.dataset.k, v.currentTime.toFixed(1));
  for (const el of $("segs").querySelectorAll("[data-play]")) el.onclick = () => { v.currentTime = cur().segments[+el.dataset.play].start; v.play(); };
  for (const el of $("segs").querySelectorAll("[data-del]")) el.onclick = () => { cur().segments.splice(+el.dataset.del, 1); cur().reviewed = false; render(); };
  draw(); list(); save();
}
function edit(i, k, val) {
  const s = cur().segments[i];
  s[k] = Math.max(0, Math.min(DATA.videos[curId].duration, +val)); s.origin = "HUMAN"; cur().reviewed = false; render();
}
function addSeg() {
  const t = +v.currentTime.toFixed(1);
  cur().segments.push({start: t, end: Math.min(t + 10, DATA.videos[curId].duration), origin: "HUMAN"}); cur().reviewed = false; render();
}
function setRev(on) {
  if (on && cur().segments.some(s => !(s.end > s.start))) { alert("Có đoạn kết thúc ≤ bắt đầu — sửa trước khi duyệt."); $("rev").checked = false; return; }
  cur().reviewed = on; render();
}
function draw() {
  const c = $("c"), g = c.getContext("2d"), p = DATA.videos[curId], n = p.scores.length || p.duration, W = c.width, H = c.height;
  g.clearRect(0, 0, W, H);
  for (const s of cur().segments) {
    g.fillStyle = s.origin === "CLAUDE_PROPOSED" ? "rgba(255,160,0,.35)" : "rgba(30,136,229,.35)";
    g.fillRect(s.start / n * W, 0, (s.end - s.start) / n * W, H);
  }
  if (p.scores.length) {
    g.strokeStyle = "#555"; g.beginPath();
    p.scores.forEach((y, i) => { const X = i / n * W, Y = H - y / 100 * H; if (i) g.lineTo(X, Y); else g.moveTo(X, Y); }); g.stroke();
    const T = H - p.threshold / 100 * H;
    g.strokeStyle = "red"; g.setLineDash([4, 4]); g.beginPath(); g.moveTo(0, T); g.lineTo(W, T); g.stroke(); g.setLineDash([]);
  }
  g.fillStyle = "#000"; g.fillRect(v.currentTime / n * W, 0, 2, H);
}
$("c").onclick = e => { const r = e.target.getBoundingClientRect(); v.currentTime = (e.clientX - r.left) / r.width * (DATA.videos[curId].scores.length || DATA.videos[curId].duration); };
v.ontimeupdate = draw;
function exportJson() {
  if (!state.rater) { alert("Nhập tên người duyệt."); return; }
  const videos = Object.entries(state.videos).filter(([, s]) => s.reviewed).map(([id, s]) => ({
    video_id: id, duration: DATA.videos[id].duration, source_sha256: DATA.videos[id].source_sha256, status: "HUMAN_VERIFIED",
    note: s.note || "", segments: s.segments.map(x => ({start: +x.start, end: +x.end, origin: x.origin}))}));
  const blob = new Blob([JSON.stringify({schema: "highlight-labels-v1", rater: state.rater, exported_at: new Date().toISOString(),
    proposals_model: DATA.model, videos: videos}, null, 1)], {type: "application/json"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "highlight_news_labels.json"; a.click();
  $("msg").textContent = "Đã xuất " + videos.length + "/" + Object.keys(DATA.videos).length + " video đã duyệt.";
}
pick(curId);
</script></body></html>"""


def main(out_dir, raw_rel, *flags):
    out = Path(out_dir)
    data = json.loads((out / "proposals.json").read_text(encoding="utf-8"))
    blind = "--blind" in flags
    hint = ("<b>Gán nhãn MÙ (tập test):</b> không có đề xuất hay điểm AI — chọn hoàn toàn theo ý bạn." if blind else
            "Đoạn màu cam = AI đề xuất (CLAUDE_PROPOSED) — sửa/xóa/thêm cho đúng ý bạn.")
    key = "ai21-news-test-labels-v1" if blind else "ai19-news-labels-v1"
    page = (PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__RAW__", json.dumps(raw_rel))
            .replace("__AIHINT__", hint).replace("__KEY__", json.dumps(key)))
    if blind:
        page = page.replace('a.download = "highlight_news_labels.json"', 'a.download = "highlight_news_test_labels.json"')
    (out / "label_news.html").write_text(page, encoding="utf-8")
    print("wrote", out / "label_news.html", "videos:", len(data["videos"]))


if __name__ == "__main__":
    main(*sys.argv[1:])
