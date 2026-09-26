// mongo-init.js — tạo collection + index (database_schema §3). T0.1b.
// Mount vào /docker-entrypoint-initdb.d/ ; chạy 1 lần khi container mongo khởi tạo.

const db = db.getSiblingDB(process.env.MONGO_APP_DB || "video_ai");

// 3.1 subtitles — phụ đề ASR
db.createCollection("subtitles");
db.subtitles.createIndex({ video_id: 1 }, { unique: true });
db.subtitles.createIndex({ "segments.text": "text" });   // text search phụ đề (GET /api/search)

// 3.2 video_analyses — điểm highlight + tóm tắt
db.createCollection("video_analyses");
db.video_analyses.createIndex({ video_id: 1 }, { unique: true });
db.video_analyses.createIndex({ summary_status: 1 });

print("[mongo-init] tạo subtitles + video_analyses + index xong");
