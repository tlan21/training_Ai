package pg

import (
	"context"
	"reflect"
	"sort"
	"strconv"
	"testing"
	"time"
)

func TestPreferenceRepository_RealReplaceRollbackAndIsolation(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	user := "usr_pref_" + strconv.FormatInt(time.Now().UnixNano(), 36)
	if _, err := db.Exec(ctx, `INSERT INTO users(id,username,email,password_hash) VALUES($1,$1,$1,'test')`, user); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _, _ = db.Exec(ctx, `DELETE FROM users WHERE id=$1`, user) })
	rows, err := db.Query(ctx, `SELECT id FROM categories ORDER BY id LIMIT 4`)
	if err != nil {
		t.Fatal(err)
	}
	ids := []string{}
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			t.Fatal(err)
		}
		ids = append(ids, id)
	}
	rows.Close()
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	if len(ids) != 4 {
		t.Fatal("need four seeded categories")
	}
	repo := &PreferenceRepo{DB: db}
	if err := repo.Replace(ctx, user, ids[:3]); err != nil {
		t.Fatal(err)
	}
	if err := repo.Replace(ctx, user, ids[1:]); err != nil {
		t.Fatal(err)
	}
	stored, err := (&PreferenceRepo{DB: db}).Get(ctx, user)
	want := append([]string{}, ids[1:]...)
	sort.Strings(want)
	if err != nil || !reflect.DeepEqual(stored, want) {
		t.Fatalf("replacement lost: %v %v", stored, err)
	}
	if err := repo.Replace(ctx, user, []string{ids[0], "cat_missing_preferences"}); err == nil {
		t.Fatal("invalid category accepted")
	}
	stored, err = repo.Get(ctx, user)
	if err != nil || !reflect.DeepEqual(stored, want) {
		t.Fatalf("failed patch deleted old preferences: %v %v", stored, err)
	}
	other, err := repo.Get(ctx, "usr_other_preferences")
	if err != nil || len(other) != 0 {
		t.Fatalf("preferences crossed user boundary: %v %v", other, err)
	}
}
