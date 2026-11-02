"""Read-only before/after fingerprints for the explicitly authorized HC-19 QA."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).parent
mode = sys.argv[1]
assert mode in ("before", "after")


def call(*args):
    return subprocess.check_output(args, text=True, encoding="utf-8").strip()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


result = {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
containers = json.loads(call("docker", "inspect", *call("docker", "ps", "-aq").splitlines()))
result["containers"] = {
    c["Name"].lstrip("/"): {
        "id": c["Id"], "image": c["Config"]["Image"], "image_id": c["Image"],
        "started_at": c["State"]["StartedAt"], "status": c["State"]["Status"],
        "env_hash": digest(sorted(c["Config"]["Env"])),
        "command_hash": digest([c["Config"].get("Entrypoint"), c["Config"].get("Cmd")]),
        "mounts": sorted(c["Mounts"], key=lambda m: m["Destination"]),
        "ports": c["HostConfig"]["PortBindings"],
    } for c in containers
}
removed = {"MILVUS_HOST", "MILVUS_PORT", "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"}
ai = next(c for c in containers if c["Name"] == "/video-ai-inference-service-1")
result["ai_env_without_storage_hash"] = digest(sorted(e for e in ai["Config"]["Env"] if e.split("=", 1)[0] not in removed))
result["ai_storage_env_keys"] = sorted(e.split("=", 1)[0] for e in ai["Config"]["Env"] if e.split("=", 1)[0] in removed)
result["postgres"] = {}
for table, key in (("videos", "id"), ("clips", "id"), ("users", "id"), ("categories", "id"),
                   ("video_processing_jobs", "id"), ("user_interactions", "id"), ("system_settings", "key")):
    sql = f"select jsonb_build_object('id',{key},'video_id',to_jsonb(t)->>'video_id','hash',md5(to_jsonb(t)::text))::text from {table} t order by {key};"
    rows = call("docker", "exec", "video-ai-postgres-1", "psql", "-X", "-U", "app", "-d", "video_ai", "-At", "-c", sql)
    result["postgres"][table] = [json.loads(row) for row in rows.splitlines()]
active = call("docker", "exec", "video-ai-postgres-1", "psql", "-X", "-U", "app", "-d", "video_ai", "-At", "-c",
              "select count(*) from video_processing_jobs where status in ('pending','running');")
assert int(active) == 0, "Active jobs; do not interrupt inference or claim cleanup"
mongo = """db.getSiblingDB('admin').auth(process.env.MONGO_INITDB_ROOT_USERNAME,process.env.MONGO_INITDB_ROOT_PASSWORD);
const app=db.getSiblingDB(process.env.MONGO_APP_DB||'video_ai'),crypto=require('crypto'),out={};
for(const name of ['video_analyses','subtitles'])out[name]=app.getCollection(name).find().sort({_id:1}).toArray().map(d=>({id:d._id.toString(),hash:crypto.createHash('sha256').update(EJSON.stringify(d)).digest('hex')}));
print(JSON.stringify(out));"""
result["mongo"] = json.loads(call("docker", "exec", "video-ai-mongo-1", "mongosh", "--quiet", "--eval", mongo).splitlines()[-1])
minio = """import os,json
from minio import Minio
c=Minio(os.environ['MINIO_ENDPOINT'],access_key=os.environ['MINIO_ACCESS_KEY'],secret_key=os.environ['MINIO_SECRET_KEY'],secure=False)
print(json.dumps({b:[{'key':o.object_name,'size':o.size,'etag':o.etag} for o in c.list_objects(b,recursive=True)] for b in ['raw-videos','clips','thumbnails']}))"""
result["minio"] = json.loads(call("docker", "exec", "video-ai-ingest-worker-1", "python", "-c", minio))
request = urllib.request.Request("http://127.0.0.1:19530/v2/vectordb/entities/query", method="POST",
                                 data=json.dumps({"collectionName": "video_frame_embeddings", "filter": "", "outputFields": ["id", "vector", "payload"], "limit": 10000, "consistencyLevel": "Strong"}).encode(),
                                 headers={"Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=30) as response:
    vectors = json.load(response)
assert vectors["code"] == 0 and len(vectors["data"]) < 10000
result["milvus"] = sorted(({"id": str(row["id"]), "hash": digest(row)} for row in vectors["data"]), key=lambda row: row["id"])
if mode == "before":
    assert not (ROOT / "INT-57-before.json").exists(), "Do not overwrite baseline"
    assert set(result["ai_storage_env_keys"]) == removed
else:
    before = json.loads((ROOT / "INT-57-before.json").read_text(encoding="utf-8"))
    own_video = sys.argv[2]
    assert own_video.startswith("vid_")
    assert result["containers"].keys() == before["containers"].keys()
    for name, old in before["containers"].items():
        new = result["containers"][name]
        if name == "video-ai-inference-service-1":
            assert old["id"] != new["id"]
            for key in ("command_hash", "mounts", "ports"):
                assert old[key] == new[key], f"Inference changed unexpectedly: {key}"
        else:
            assert old == new, f"Other container changed: {name}"
    assert not result["ai_storage_env_keys"]
    assert result["ai_env_without_storage_hash"] == before["ai_env_without_storage_hash"]
    extras = {}
    for table, original in before["postgres"].items():
        current = {row["id"]: row for row in result["postgres"][table]}
        assert all(current.get(row["id"]) == row for row in original), f"Original PostgreSQL rows changed: {table}"
        original_ids = {row["id"] for row in original}
        extra = [row for row in current.values() if row["id"] not in original_ids]
        assert all((table == "videos" and row["id"] == own_video) or (table in ("clips", "video_processing_jobs") and row["video_id"] == own_video) for row in extra), f"Unexpected new row: {table}"
        extras[table] = [row["id"] for row in extra]
    for name in ("mongo", "minio", "milvus"):
        assert result[name] == before[name], f"Original {name} changed or QA artifacts remain"
    result["verification"] = {"original_data_preserved": True, "other_containers_unchanged": len(before["containers"]) - 1,
                              "only_own_postgres_tombstones": extras, "own_video": own_video, "PASS": True}
(ROOT / f"INT-57-{mode}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"mode": mode, "pg_counts": {k: len(v) for k, v in result["postgres"].items()},
                  "mongo_counts": {k: len(v) for k, v in result["mongo"].items()}, "vectors": len(result["milvus"]),
                  "objects": {k: len(v) for k, v in result["minio"].items()}, "verification": result.get("verification")}))
