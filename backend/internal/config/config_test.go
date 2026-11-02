package config

import "testing"

func TestStubRequiresExplicitOptIn(t *testing.T) {
	for _, value := range []string{"", "0", "true", "1"} {
		t.Setenv("AI_ALLOW_STUB", value)
		if got := Load().AIAllowStub; got != (value == "1") {
			t.Fatalf("AI_ALLOW_STUB=%q: got %t", value, got)
		}
	}
}
