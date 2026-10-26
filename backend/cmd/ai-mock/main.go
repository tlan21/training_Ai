// ai-mock serves deterministic AI-API fixtures; it never loads checkpoints.
package main

import (
	"log"
	"net/http"
	"os"
	"time"

	"traning_ai/backend/internal/mocks"
)

func main() {
	key := os.Getenv("AI_SERVICE_KEY")
	if key == "" {
		log.Fatal("AI_SERVICE_KEY is required")
	}
	log.Print("MOCK_ONLY AI HTTP :8001, stub_mode=true, no models loaded")
	server := &http.Server{Addr: ":8001", Handler: mocks.NewAIHTTP(key), ReadHeaderTimeout: 5 * time.Second}
	log.Fatal(server.ListenAndServe())
}
