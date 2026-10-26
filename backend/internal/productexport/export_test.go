package productexport

import (
	"testing"
)

func TestExportFieldTypes(t *testing.T) {
	for _, tc := range []struct {
		body  string
		valid bool
	}{
		{`{"user_id":"usr_a","created_at":"2026-10-26T00:00:00Z","preferred_category_ids":[]}`, true},
		{`{"category_id":null,"duration_seconds":1.5,"visible_to_client":true}`, true},
		{`{"clip_id":null,"interaction_id":123,"duration_watched":0}`, true},
		{`{"duration_watched":null}`, false}, {`{"interaction_id":1.5}`, false},
		{`{"visible_to_client":"true"}`, false}, {`{"created_at":null}`, false},
		{`{"duration_seconds":"NaN"}`, false}, {`{"preferred_category_ids":null}`, false},
	} {
		if err := validateRow("test", []byte(tc.body)); (err == nil) != tc.valid {
			t.Errorf("%s: %v", tc.body, err)
		}
	}
}
