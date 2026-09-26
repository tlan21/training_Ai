# infra — hạ tầng dev (T0.1)

docker-compose 1 máy cho 6 dịch vụ backend. Không dính AI (inference-service riêng).

## Dịch vụ & cổng

| Dịch vụ | Image | Cổng | Ghi chú |
|---|---|---|---|
| PostgreSQL | postgres:16 | `5432` | nguồn sự thật; auto-init schema + seed |
| MongoDB | mongo:7 | `27017` | subtitles, video_analyses; auto-init index |
| Redis | redis:7 | `6379` | cache feed/search |
| MinIO | minio | `9000` API · `9001` console | bucket `videos` (app) + `milvus` |
| Milvus | milvus:v2.4.9 (+etcd) | `19530` SDK · `9091` health | 2 collection tạo bằng script |
| Kafka | bitnami/kafka:3.7 (KRaft) | `9092` | event bus, auto-create topics |

## Chạy

```bash
cp infra/.env.example infra/.env         # sửa mật khẩu nếu cần
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps    # chờ tất cả healthy
```

## Khởi tạo tự động

- **Postgres**: `postgres/init/001_schema.sql` (12 bảng + index) + `002_seed.sql`
  (10 danh mục, admin `admin/admin123`, 6 system_settings) — chạy 1 lần khi volume trống.
- **Mongo**: `mongo/init/mongo-init.js` — collection + index (unique `video_id`, text index `segments.text`).
- **MinIO**: service `minio-init` tạo bucket `videos` + `milvus` rồi thoát.

## Milvus collection (chạy tay sau khi milvus healthy)

```bash
pip install pymilvus
python infra/milvus/init_collections.py      # tạo video_frame_embeddings (HNSW/COSINE) + user_recommendation_embeddings (IVF_FLAT/IP)
```

## Kiểm tra nhanh

```bash
# Postgres: seed đúng?
docker compose -f infra/docker-compose.yml exec postgres \
  psql -U app -d video_ai -c "SELECT key,value FROM system_settings; SELECT count(*) FROM categories;"

# Mongo: index?
docker compose -f infra/docker-compose.yml exec mongo \
  mongosh video_ai --quiet --eval "db.subtitles.getIndexes()"

# Milvus: collection?
python infra/milvus/init_collections.py       # in list_collections ở cuối
```

## Dừng / xóa

```bash
docker compose -f infra/docker-compose.yml down          # giữ volume (dữ liệu còn)
docker compose -f infra/docker-compose.yml down -v       # xóa sạch volume (init lại từ đầu)
```

## Lưu ý

- Đổi `MINIO_ROOT_*`, mật khẩu Postgres/Mongo, và `ai_service_api_key` (seed placeholder `sk-local-CHANGE-ME`)
  trước khi chạy production.
- Admin seed `admin123` chỉ để dev — đổi ngay ở môi trường thật.
- Milvus dùng chung MinIO (bucket `milvus`), tách với bucket `videos` của app.
