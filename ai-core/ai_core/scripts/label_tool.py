"""T1.2e — tool gan nhan noi bo (dataset_spec 4).

Mo 1 trang web don gian: chon category cho video + keo vung highlight tren timeline.
Tai dung UI heatmap cua CMS sau nay; day la ban toi thieu chay bang stdlib.

Dung:
  .venv/Scripts/python.exe -m ai_core.scripts.label_tool --port 8010 --video-dir D:/data_training_ai/data/raw/videos
Mo http://localhost:8010 — chon video, chon lop, keo 2 tay cat highlight, Save.

Ghi ra:
  data/labels/categories.json  {video_id: category}   (ghi de)
  data/labels/highlight/{video_id}.json  [{start, end}]  (giay, theo video goc)
"""
import argparse, http.server, json, os, pathlib, urllib.parse

CATEGORIES = ["bong_da", "the_thao", "ca_nhac", "tin_tuc"]  # MVP 4 lop (CLAUDE.md)

HTML = r"""<!doctype html><meta charset="utf-8"><title>Label Tool — T1.2e</title>
<style>body{font-family:system-ui;max-width:900px;margin:24px auto;padding:0 16px}video{width:100%;background:#111} 
#tl{height:48px;background:#eee;position:relative;margin:12px 0;cursor:pointer;border-radius:8px}
#sel{position:absolute;top:0;height:100%;background:#4f8cff66;border:2px solid #4f8cff;border-radius:8px}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap} button{padding:8px 14px}</style>
<h2>Tool gán nhãn — T1.2e (category + highlight)</h2>
<div class=row>
 <select id="vid"></select>
 <select id="cat"><option value="">--category--</option></select>
 <button id="saveCat">Save category</button>
 <span id="catMsg"></span>
</div>
<video id="v" controls></video>
<div id="tl"><div id="sel"></div></div>
<div class=row>
 <label>start <input id="s" type="number" step="0.1" style="width:80px"></label>
 <label>end <input id="e" type="number" step="0.1" style="width:80px"></label>
 <button id="add">Add interval</button>
 <button id="saveHl">Save highlight</button>
</div>
<pre id="hl"></pre>
<script>
let intervals=[]; let vid="";
const $=id=>document.getElementById(id);
async function loadVideos(){
  const j=await (await fetch("/api/videos")).json();
  $("vid").innerHTML=j.videos.map(v=>`<option value="${v.id}">${v.id} — ${v.duration||"?"}s</option>`).join("");
  $("cat").innerHTML='<option value="">--category--</option>'+["bong_da","the_thao","ca_nhac","tin_tuc"].map(c=>`<option>${c}</option>`).join("");
  if(j.videos[0]) pick(j.videos[0].id);
}
async function pick(id){
  vid=id; intervals=[];
  const j=await (await fetch("/api/labels?video_id="+encodeURIComponent(id))).json();
  if(j.category) $("cat").value=j.category;
  intervals=j.highlight||[];
  $("v").src=j.video_url||""; render();
}
function render(){
  $("hl").textContent=JSON.stringify(intervals,null,2);
  draw();
}
function draw(){
  const d=$("v").duration||60, tl=$("tl"), sel=$("sel");
  if(!d||!intervals.length){ sel.style.display="none"; return; }
  // hien vung dau tien lam demo
  const a=intervals[0]; sel.style.display="block";
  sel.style.left=(a.start/d*100)+"%"; sel.style.width=((a.end-a.start)/d*100)+"%";
}
$("vid").onchange=e=>pick(e.target.value);
$("v").onloadedmetadata=draw;
$("tl").onclick=e=>{
  const d=$("v").duration||60, r=$("tl").getBoundingClientRect();
  const t=(e.clientX-r.left)/r.width*d;
  if(!intervals.length) intervals.push({start:Math.max(0,t-2),end:Math.min(d,t+3)});
  else { intervals[0].start=Math.max(0,t-2); intervals[0].end=Math.min(d,t+3); }
  $("s").value=intervals[0].start.toFixed(1); $("e").value=intervals[0].end.toFixed(1); render();
};
$("add").onclick=()=>{
  const a=parseFloat($("s").value), b=parseFloat($("e").value);
  if(!(a<b)) return alert("start < end");
  intervals.push({start:a,end:b}); render();
};
$("saveCat").onclick=async()=>{
  const c=$("cat").value; if(!c) return alert("chon category");
  const r=await fetch("/api/labels",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({video_id:vid,category:c})});
  $("catMsg").textContent=r.ok?"saved":"fail";
};
$("saveHl").onclick=async()=>{
  const r=await fetch("/api/labels",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({video_id:vid,highlight:intervals})});
  alert(r.ok?"saved highlight":"fail");
};
loadVideos();
</script>
"""

class H(http.server.BaseHTTPRequestHandler):
    video_dir: pathlib.Path
    label_dir: pathlib.Path

    def log_message(self, fmt, *a): pass  # ponytail: less log noise

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/":
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(HTML.encode()); return
        if u.path == "/api/videos":
            vids=[]
            if self.video_dir.is_dir():
                for p in sorted(self.video_dir.iterdir()):
                    if p.is_file():
                        vids.append({"id": p.stem, "video_url": f"/raw/{urllib.parse.quote(p.name)}", "duration": None})
            if not vids:  # mock khi chua co video
                vids=[{"id":"demo_001","video_url":"","duration":60}]
            self._json({"videos": vids}); return
        if u.path == "/api/labels":
            q = urllib.parse.parse_qs(u.query)
            vid = (q.get("video_id") or [""])[0]
            cat = None; hl=[]
            cf = self.label_dir / "categories.json"
            if cf.exists():
                try: cat = json.load(open(cf,encoding="utf-8")).get(vid)
                except: pass
            hf = self.label_dir / "highlight" / f"{vid}.json"
            if hf.exists():
                try: hl = json.load(open(hf,encoding="utf-8"))
                except: pass
            # video_url
            url=""
            for ext in (".mp4",".ogv",".mkv",".webm"):
                cand = self.video_dir / f"{vid}{ext}"
                if cand.exists(): url = f"/raw/{urllib.parse.quote(cand.name)}"; break
            self._json({"video_id": vid, "category": cat, "highlight": hl, "video_url": url}); return
        if u.path.startswith("/raw/"):
            name = urllib.parse.unquote(u.path[len("/raw/"):])
            fp = self.video_dir / name
            if fp.is_file():
                self.send_response(200); self.send_header("Content-Type","video/mp4"); self.send_header("Content-Length", str(fp.stat().st_size)); self.end_headers()
                self.wfile.write(fp.read_bytes()); return
            self.send_error(404); return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/labels": self.send_error(404); return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0)) or 0) or b"{}")
        vid = body.get("video_id")
        if not vid: self._json({"error":"missing video_id"},422); return
        self.label_dir.mkdir(parents=True, exist_ok=True)
        if "category" in body:
            if body["category"] not in CATEGORIES: self._json({"error":"invalid category"},400); return
            cf = self.label_dir / "categories.json"
            d = json.load(open(cf,encoding="utf-8")) if cf.exists() else {}
            d[vid]=body["category"]
            json.dump(d, open(cf,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        if "highlight" in body:
            (self.label_dir / "highlight").mkdir(parents=True, exist_ok=True)
            hf = self.label_dir / "highlight" / f"{vid}.json"
            # sort + clamp
            ivs = sorted(body["highlight"], key=lambda x: x["start"])
            json.dump(ivs, open(hf,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        self._json({"ok": True})

    def _json(self, obj, code=200):
        b=json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8"); self.end_headers()
        self.wfile.write(b)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8010)
    ap.add_argument("--video-dir", default="data/raw/videos")
    ap.add_argument("--label-dir", default="data/labels")
    a=ap.parse_args()
    H.video_dir=pathlib.Path(a.video_dir); H.label_dir=pathlib.Path(a.label_dir)
    print(f"label_tool http://localhost:{a.port}  video_dir={H.video_dir}  label_dir={H.label_dir}")
    http.server.ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()

if __name__=="__main__": main()
