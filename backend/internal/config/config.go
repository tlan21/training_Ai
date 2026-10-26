package config

import "os"

// Config — env cho gateway + workers (02_backend_plan.md §2/§7 2.1.8).
// Mặc định đều trỏ local/docker-compose; thiếu DB thì adapter trả ErrNotFound, gateway vẫn chạy với mocks.
type Config struct {
	Port                string
	AIBaseURL           string
	AIServiceKey        string
	AIAllowStub         bool
	PostgresDSN         string
	MongoURI            string
	MongoDB             string
	MilvusHost          string
	MilvusPort          string
	KafkaBrokers        string
	MinioEndpoint       string
	MinioPublicEndpoint string
	MinioAccess         string
	MinioSecret         string
	MinioBucket         string
	RedisAddr           string
	JWTSecret           string
}

func Load() Config {
	return Config{
		Port:                env("GATEWAY_PORT", "8000"),
		AIBaseURL:           env("AI_BASE_URL", "http://localhost:8001"),
		AIServiceKey:        env("AI_SERVICE_KEY", "sk-local-dev-key"),
		AIAllowStub:         os.Getenv("AI_ALLOW_STUB") == "1",
		PostgresDSN:         env("POSTGRES_DSN", "postgres://postgres:postgres@localhost:5432/traning_ai?sslmode=disable"),
		MongoURI:            env("MONGO_URI", "mongodb://localhost:27017"),
		MongoDB:             env("MONGO_DB", "traning_ai"),
		MilvusHost:          env("MILVUS_HOST", "localhost"),
		MilvusPort:          env("MILVUS_PORT", "19530"),
		KafkaBrokers:        env("KAFKA_BROKERS", "localhost:9092"),
		MinioEndpoint:       env("MINIO_ENDPOINT", "localhost:9000"),
		MinioPublicEndpoint: env("MINIO_PUBLIC_ENDPOINT", "localhost:9000"),
		MinioAccess:         env("MINIO_ACCESS_KEY", "minioadmin"),
		MinioSecret:         env("MINIO_SECRET_KEY", "minioadmin"),
		MinioBucket:         env("MINIO_BUCKET", "raw-videos"),
		RedisAddr:           env("REDIS_ADDR", "localhost:6379"),
		JWTSecret:           env("JWT_SECRET", "dev-jwt-secret-change-me"),
	}
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
