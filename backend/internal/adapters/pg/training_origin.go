package pg

import "strings"

func trainingOrigin(configured string, names ...string) string {
	for _, name := range names {
		name = strings.ToLower(strings.TrimSpace(name))
		if strings.HasSuffix(name, "@example.test") || strings.HasSuffix(name, "@example.com") {
			return "test"
		}
		for _, prefix := range []string{"e2e-", "int02-", "int04-", "int-", "t4-", "demo-", "test-"} {
			if strings.HasPrefix(name, prefix) {
				return "test"
			}
		}
	}
	if configured == "product" || configured == "test" {
		return configured
	}
	return "unknown"
}
