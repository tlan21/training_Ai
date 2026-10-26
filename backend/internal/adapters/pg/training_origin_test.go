package pg

import "testing"

func TestTrainingOrigin(t *testing.T) {
	for _, tc := range []struct{ configured, name, want string }{
		{"", "real", "unknown"}, {"invalid", "real", "unknown"}, {"product", "real", "product"},
		{"test", "real", "test"}, {"product", "E2E-int16-123", "test"}, {"product", "INT-02-MOCK_ONLY-probe", "test"},
		{"product", "probe@example.test", "test"}, {"product", "Demo-video", "test"},
	} {
		if got := trainingOrigin(tc.configured, tc.name); got != tc.want {
			t.Errorf("%+v got %s", tc, got)
		}
	}
}
