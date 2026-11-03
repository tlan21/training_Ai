"""INT-50 real QA: read-only before/after fingerprints (adapted from coordination/codex/verification/INT-57-preservation.py).

  python coordination/claude/evidence/INT-50_2026-11-02/preservation.py before|after
Original rows/documents/objects/vectors must be byte-identical after QA. The only allowed extras are Claude QA artifacts:
videos/categories whose title/name starts with "CLAUDE-QA", and clips/jobs/interactions/Mongo docs/MinIO keys/vectors tied to those videos.
system_settings compare key+value (restoring a flag rewrites updated_at). No secret is printed (settings values are hashed).
"""
import base64
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).parent
PREFIX = "CLAUDE-QA"
mode = sys.argv[1]
assert mode in ("before", "after")


def call(*args):
    return subprocess.check_output(args, text=True, encoding="utf-8").strip()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def psql(sql):
    return call("docker", "exec", "video-ai-postgres-1", "psql", "-X", "-U", "app", "-d", "video_ai", "-At", "-c", sql)


result = {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
containers = json.loads(call("docker", "inspect", *call("docker", "ps", "-aq").splitlines()))
result["containers"] = {c["Name"].lstrip("/"): {"id": c["Id"], "image_id": c["Image"], "started_at": c["State"]["StartedAt"],
                                                 "env_hash": digest(sorted(c["Config"]["Env"]))} for c in containers}
result["postgres"] = {}
for table, label in (("videos", "title"), ("clips", "title"), ("users", "username"), ("categories", "name"),
                     ("video_processing_jobs", None), ("user_interactions", None)):
    extra = f",'label',t.{label}" if label else ""
    sql = (f"select jsonb_build_object('id',id,'video_id',to_jsonb(t)->>'video_id','hash',md5(to_jsonb(t)::text){extra})::text "
           f"from {table} t order by id;")
    result["postgres"][table] = [json.loads(r) for r in psql(sql).splitlines()]
result["postgres"]["system_settings"] = [json.loads(r) for r in psql(
    "select jsonb_build_object('id',key,'hash',md5(value::text))::text from system_settings order by key;").splitlines()]
assert int(psql("select count(*) from video_processing_jobs where status in ('pending','running');")) == 0, "Active jobs — wait"
mongo = """db.getSiblingDB('admin').auth(process.env.MONGO_INITDB_ROOT_USERNAME,process.env.MONGO_INITDB_ROOT_PASSWORD);
const app=db.getSiblingDB(process.env.MONGO_APP_DB||'video_ai'),crypto=require('crypto'),out={};
for(const name of ['video_analyses','subtitles'])out[name]=app.getCollection(name).find().sort({_id:1}).toArray().map(d=>({id:d._id.toString(),video_id:d.video_id||null,hash:crypto.createHash('sha256').update(EJSON.stringify(d)).digest('hex')}));
print(JSON.stringify(out));"""
result["mongo"] = json.loads(call("docker", "exec", "video-ai-mongo-1", "mongosh", "--quiet", "--eval", mongo).splitlines()[-1])
minio = """import os,json
from minio import Minio
c=Minio(os.environ['MINIO_ENDPOINT'],access_key=os.environ['MINIO_ACCESS_KEY'],secret_key=os.environ['MINIO_SECRET_KEY'],secure=False)
print(json.dumps({b:[{'key':o.object_name,'size':o.size,'etag':o.etag} for o in c.list_objects(b,recursive=True)] for b in ['raw-videos','clips','thumbnails']}))"""
result["minio"] = json.loads(call("docker", "exec", "video-ai-ingest-worker-1", "python", "-c", minio))
req = urllib.request.Request("http://127.0.0.1:19530/v2/vectordb/entities/query", method="POST", headers={"Content-Type": "application/json"},
                             data=json.dumps({"collectionName": "video_frame_embeddings", "filter": "", "outputFields": ["id", "vector", "payload"],
                                              "limit": 10000, "consistencyLevel": "Strong"}).encode())
with urllib.request.urlopen(req, timeout=30) as r:
    vectors = json.load(r)
assert vectors["code"] == 0 and len(vectors["data"]) < 10000
def _video_id(payload):
    if isinstance(payload, str):                    # REST returns JSON fields as strings (sometimes empty)
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            try:                                    # JSON field may come back base64-encoded
                payload = json.loads(base64.b64decode(payload))
            except (ValueError, json.JSONDecodeError):
                return None
    return (payload or {}).get("video_id")


result["milvus"] = sorted(({"id": str(v["id"]), "video_id": _video_id(v.get("payload")), "hash": digest(v)} for v in vectors["data"]),
                          key=lambda v: v["id"])

out = ROOT / f"preservation_{mode}.json"
if mode == "before":
    assert not out.exists(), "Do not overwrite baseline"
else:
    before = json.loads((ROOT / "preservation_before.json").read_text(encoding="utf-8"))
    own_videos = {r["id"] for r in result["postgres"]["videos"] if (r.get("label") or "").startswith(PREFIX)}
    report = {"own_videos": sorted(own_videos), "extras": {}, "problems": []}
    for table, original in before["postgres"].items():
        cur = {r["id"]: r for r in result["postgres"][table]}
        for r in original:
            if cur.get(r["id"]) != r:
                report["problems"].append(f"original {table} row changed/removed: {r['id']}")
        ids = {r["id"] for r in original}
        extra = [r for r in cur.values() if r["id"] not in ids]
        for r in extra:
            ok = (r.get("label") or "").startswith(PREFIX) or r.get("video_id") in own_videos
            if not ok:
                report["problems"].append(f"unexpected new {table} row: {r['id']}")
        report["extras"][table] = [r["id"] for r in extra]
    for coll, original in before["mongo"].items():
        cur = {d["id"]: d for d in result["mongo"][coll]}
        report["problems"] += [f"original mongo {coll} changed: {d['id']}" for d in original if cur.get(d["id"]) != d]
        ids = {d["id"] for d in original}
        report["extras"][f"mongo.{coll}"] = [d["id"] for d in cur.values() if d["id"] not in ids]
        report["problems"] += [f"unexpected mongo {coll}: {d['id']}" for d in cur.values() if d["id"] not in ids and d["video_id"] not in own_videos]
    for bucket, original in before["minio"].items():
        cur = {o["key"]: o for o in result["minio"][bucket]}
        report["problems"] += [f"original object changed: {bucket}/{o['key']}" for o in original if cur.get(o["key"]) != o]
        ids = {o["key"] for o in original}
        new = [k for k in cur if k not in ids]
        report["extras"][f"minio.{bucket}"] = new
        report["problems"] += [f"unexpected object {bucket}/{k}" for k in new if not any(v in k for v in own_videos)]
    cur = {v["id"]: v for v in result["milvus"]}
    report["problems"] += [f"original vector changed: {v['id']}" for v in before["milvus"] if cur.get(v["id"], {}).get("hash") != v["hash"]]
    ids = {v["id"] for v in before["milvus"]}
    report["extras"]["milvus"] = [v["id"] for v in cur.values() if v["id"] not in ids]
    report["problems"] += [f"unexpected vector {v['id']}" for v in cur.values() if v["id"] not in ids and v["video_id"] not in own_videos]
    changed = [n for n, c in before["containers"].items() if result["containers"].get(n) != c]
    report["containers_changed"] = changed
    report["PASS"] = not report["problems"]
    result["verification"] = report
out.write_text(json.dumps(result, indent=1), encoding="utf-8")
print(json.dumps({"mode": mode, "pg": {k: len(v) for k, v in result["postgres"].items()}, "mongo": {k: len(v) for k, v in result["mongo"].items()},
                  "minio": {k: len(v) for k, v in result["minio"].items()}, "vectors": len(result["milvus"]),
                  "verification": {k: v for k, v in result.get("verification", {}).items() if k != "extras"} or None}))
