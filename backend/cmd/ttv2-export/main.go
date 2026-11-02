package main

import (
	"context"
	"encoding/json"
	"flag"
	"log"
	"os"
	"time"

	"traning_ai/backend/internal/adapters/pg"
	"traning_ai/backend/internal/productexport"
)

var revision string

func main() {
	out := flag.String("out", "", "new bundle directory (must not exist)")
	environment := flag.String("environment", "local", "local, staging or prod")
	flag.Parse()
	if *out == "" || os.Getenv("POSTGRES_DSN") == "" || revision == "" {
		log.Fatal("out, POSTGRES_DSN and build-time revision are required")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	db, err := pg.New(ctx, os.Getenv("POSTGRES_DSN"))
	if err != nil {
		log.Fatal("database connection failed")
	}
	defer db.Close()
	manifest, err := productexport.Export(ctx, db, *out, *environment, revision)
	if err != nil {
		log.Fatal(err)
	}
	if err = json.NewEncoder(os.Stdout).Encode(manifest); err != nil {
		log.Fatal(err)
	}
}
