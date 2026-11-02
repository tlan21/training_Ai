package productexport

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

func TestRealSnapshotProvenanceAndChecksums(t *testing.T) {
	dsn := os.Getenv("TEST_POSTGRES_DSN")
	if dsn == "" {
		t.Skip("set TEST_POSTGRES_DSN for real PostgreSQL")
	}
	ctx := context.Background()
	db, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(db.Close)
	suffix := strconv.FormatInt(time.Now().UnixNano(), 36)
	user := "usr_export_" + suffix
	video := "vid_export_" + suffix
	clip := "clp_export_" + suffix
	users := []string{user, user + "test", user + "unknown", user + "admin"}
	videos := []string{video, video + "test", video + "unknown"}
	exec := func(query string, args ...any) {
		t.Helper()
		if _, err := db.Exec(ctx, query, args...); err != nil {
			t.Fatal(err)
		}
	}
	t.Cleanup(func() {
		if _, err := db.Exec(ctx, `DELETE FROM videos WHERE id=ANY($1::text[])`, videos); err != nil {
			t.Errorf("fixture cleanup videos: %v", err)
		}
		if _, err := db.Exec(ctx, `DELETE FROM users WHERE id=ANY($1::text[])`, users); err != nil {
			t.Errorf("fixture cleanup users: %v", err)
		}
	})
	exec(`INSERT INTO users(id,username,email,password_hash,role,training_origin) VALUES
	($1,$1,$1,'private-hash','client','product'),($2,$2,$2,'private-hash','client','test'),
	($3,$3,$3,'private-hash','client','unknown'),($4,$4,$4,'private-hash','admin','product')`, users[0], users[1], users[2], users[3])
	exec(`INSERT INTO videos(id,title,raw_file_path,duration_seconds,status,training_origin) VALUES
	($1,'private-title','private-path',10,'processed','product'),($2,'test','test',10,'processed','test'),($3,'unknown','unknown',10,'processed','unknown')`, videos[0], videos[1], videos[2])
	exec(`INSERT INTO clips(id,video_id,title,start_time,end_time,average_score,status) VALUES($1,$2,'private-title',0,5,80,'published')`, clip, video)
	for _, uid := range users {
		for _, vid := range videos {
			exec(`INSERT INTO user_interactions(user_id,video_id,interaction_type,duration_watched) VALUES($1,$2,'watch_time',3)`, uid, vid)
		}
	}
	// Future events are not part of the snapshot.
	exec(`INSERT INTO user_interactions(user_id,video_id,interaction_type,created_at) VALUES($1,$2,'like',now()+interval '1 day')`, user, video)
	out := filepath.Join(t.TempDir(), "bundle")
	m, err := Export(ctx, db, out, "local", "test-fixture")
	if err != nil {
		t.Fatal(err)
	}
	if m.Version != "ttv2-data-v1.1" || m.Provenance.Source != "product_postgres" || m.Provenance.Exporter != "ttv2-export@test-fixture" || m.SnapshotAt.Location() != time.UTC {
		t.Fatalf("manifest: %+v", m)
	}
	for name, info := range m.Files {
		body, err := os.ReadFile(filepath.Join(out, name))
		if err != nil {
			t.Fatal(err)
		}
		hash := sha256.Sum256(body)
		if hex.EncodeToString(hash[:]) != info.SHA256 {
			t.Fatal("checksum mismatch")
		}
		lines := strings.Split(strings.TrimSpace(string(body)), "\n")
		if len(body) == 0 {
			lines = nil
		}
		if int64(len(lines)) != info.Rows {
			t.Fatal("row count mismatch")
		}
		for _, line := range lines {
			if !json.Valid([]byte(line)) || strings.Contains(line, "private-") {
				t.Fatal("invalid JSON/PII payload")
			}
			for _, excluded := range append(users[1:], videos[1:]...) {
				if strings.Contains(line, `"`+excluded+`"`) {
					t.Fatal("test/unknown/admin leaked")
				}
			}
		}
	}
	interactions, err := os.ReadFile(filepath.Join(out, "interactions.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	if strings.Count(string(interactions), user+`"`) != 1 {
		t.Fatal("eligible event missing or future event included")
	}
	second, err := Export(ctx, db, filepath.Join(t.TempDir(), "bundle"), "local", "test-fixture")
	if err != nil {
		t.Fatal(err)
	}
	for name, info := range m.Files {
		if second.Files[name] != info {
			t.Fatalf("nondeterministic file: %s", name)
		}
	}
	if _, err = Export(ctx, db, out, "local", "test-fixture"); err == nil {
		t.Fatal("existing bundle overwritten")
	}
}
