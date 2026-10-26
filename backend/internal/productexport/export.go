// Package productexport writes the read-only HC-09 bundle; labels and training belong to Claude.
package productexport

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type File struct {
	Rows   int64  `json:"rows"`
	SHA256 string `json:"sha256"`
}
type Provenance struct {
	Source      string `json:"source"`
	Exporter    string `json:"exporter"`
	Environment string `json:"environment"`
}
type Manifest struct {
	Version     string          `json:"export_version"`
	GeneratedAt time.Time       `json:"generated_at"`
	SnapshotAt  time.Time       `json:"snapshot_at"`
	Files       map[string]File `json:"files"`
	Provenance  Provenance      `json:"provenance"`
}

const eligible = `WITH eu AS (SELECT * FROM users WHERE role='client' AND training_origin='product'),
ev AS (SELECT * FROM videos WHERE training_origin='product') `
const utc = `'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'`

var queries = []struct{ name, sql string }{
	{"users.jsonl", eligible + `SELECT json_build_object('user_id',u.id,'created_at',to_char(u.created_at AT TIME ZONE 'UTC',` + utc + `),
	'preferred_category_ids',ARRAY(SELECT category_id FROM user_preferences WHERE user_id=u.id ORDER BY category_id)) FROM eu u ORDER BY u.id`},
	{"categories.jsonl", `SELECT json_build_object('category_id',id,'name',name) FROM categories ORDER BY id`},
	{"videos.jsonl", eligible + `SELECT json_build_object('video_id',v.id,'category_id',v.category_id,'duration_seconds',v.duration_seconds,
	'visible_to_client',v.status='processed' AND v.deleted_at IS NULL,
	'created_at',to_char(v.created_at AT TIME ZONE 'UTC',` + utc + `)) FROM ev v ORDER BY v.id`},
	{"clips.jsonl", eligible + `SELECT json_build_object('clip_id',c.id,'video_id',c.video_id,'start_time',c.start_time,'end_time',c.end_time,'status',c.status)
	FROM clips c JOIN ev v ON v.id=c.video_id ORDER BY c.id`},
	{"interactions.jsonl", eligible + `SELECT json_build_object('interaction_id',i.id,'user_id',i.user_id,'video_id',i.video_id,'clip_id',i.clip_id,
	'interaction_type',i.interaction_type,'duration_watched',i.duration_watched,'created_at',to_char(i.created_at AT TIME ZONE 'UTC',` + utc + `))
	FROM user_interactions i JOIN eu u ON u.id=i.user_id JOIN ev v ON v.id=i.video_id WHERE i.created_at<=$1 ORDER BY i.id`},
}

// Export never overwrites a directory. Manifest is written last; consumers must validate it before use.
func Export(ctx context.Context, db *pgxpool.Pool, out, environment, revision string) (*Manifest, error) {
	if environment != "local" && environment != "staging" && environment != "prod" {
		return nil, fmt.Errorf("invalid environment")
	}
	if revision == "" {
		return nil, fmt.Errorf("exporter revision required")
	}
	if err := os.MkdirAll(filepath.Dir(out), 0750); err != nil {
		return nil, err
	}
	if err := os.Mkdir(out, 0750); err != nil {
		return nil, err
	}
	tx, err := db.BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.RepeatableRead, AccessMode: pgx.ReadOnly})
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)
	m := &Manifest{Version: "ttv2-data-v1.1", Files: map[string]File{}, Provenance: Provenance{"product_postgres", "ttv2-export@" + revision, environment}}
	if err = tx.QueryRow(ctx, `SELECT transaction_timestamp()`).Scan(&m.SnapshotAt); err != nil {
		return nil, err
	}
	m.SnapshotAt = m.SnapshotAt.UTC()
	for _, q := range queries {
		var args []any
		if q.name == "interactions.jsonl" {
			args = []any{m.SnapshotAt}
		}
		rows, err := tx.Query(ctx, q.sql, args...)
		if err != nil {
			return nil, fmt.Errorf("%s query: %w", q.name, err)
		}
		info, err := writeRows(filepath.Join(out, q.name), q.name, rows)
		rows.Close()
		if err != nil {
			return nil, fmt.Errorf("%s: %w", q.name, err)
		}
		m.Files[q.name] = info
	}
	if err = tx.Commit(ctx); err != nil {
		return nil, err
	}
	m.GeneratedAt = time.Now().UTC()
	file, err := os.OpenFile(filepath.Join(out, "manifest.json"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0640)
	if err != nil {
		return nil, err
	}
	err = json.NewEncoder(file).Encode(m)
	closeErr := file.Close()
	if err != nil {
		return nil, err
	}
	if closeErr != nil {
		return nil, closeErr
	}
	return m, nil
}

func writeRows(path, name string, rows pgx.Rows) (File, error) {
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0640)
	if err != nil {
		return File{}, err
	}
	hash := sha256.New()
	writer := io.MultiWriter(file, hash)
	var count int64
	for rows.Next() {
		var line []byte
		if err = rows.Scan(&line); err != nil {
			break
		}
		if err = validateRow(name, line); err != nil {
			break
		}
		if _, err = writer.Write(append(line, '\n')); err != nil {
			break
		}
		count++
	}
	if err == nil {
		err = rows.Err()
	}
	closeErr := file.Close()
	if err == nil {
		err = closeErr
	}
	return File{count, hex.EncodeToString(hash.Sum(nil))}, err
}

// SQL constructs the exact fields; reject nullable legacy values instead of fabricating them.
func validateRow(name string, line []byte) error {
	var row map[string]json.RawMessage
	if err := json.Unmarshal(line, &row); err != nil {
		return err
	}
	for key, value := range row {
		var parsed any
		if err := json.Unmarshal(value, &parsed); err != nil {
			return err
		}
		valid := false
		switch key {
		case "category_id", "clip_id":
			_, valid = parsed.(string)
			valid = valid || parsed == nil
		case "duration_seconds", "start_time", "end_time":
			_, valid = parsed.(float64)
		case "interaction_id", "duration_watched":
			var number int64
			valid = json.Unmarshal(value, &number) == nil && parsed != nil
		case "visible_to_client":
			_, valid = parsed.(bool)
		case "preferred_category_ids":
			var values []string
			valid = json.Unmarshal(value, &values) == nil && values != nil
		default:
			_, valid = parsed.(string)
		}
		if !valid {
			return fmt.Errorf("%s invalid field type: %s", name, key)
		}
	}
	return nil
}
