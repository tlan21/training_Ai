package config

import "os"

// Config — env cho gateway (mở rộng ở Phase 2: DSN, brokers, JWT keys...).
type Config struct {
	Port         string
	AIBaseURL    string // inference-service :8001
	AIServiceKey string // sk-local-...
}

func Load() Config {
	return Config{
		Port:         env("GATEWAY_PORT", "8000"),
		AIBaseURL:    env("AI_BASE_URL", "http://localhost:8001"),
		AIServiceKey: env("AI_SERVICE_KEY", "sk-local-dev-key"),
	}
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
