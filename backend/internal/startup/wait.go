// Package startup bounds dependency readiness checks before a service accepts requests.
package startup

import (
	"context"
	"errors"
	"fmt"
	"log"
	"time"
)

func Wait(ctx context.Context, name string, check func(context.Context) error) error {
	ctx, cancel := context.WithTimeout(ctx, 90*time.Second)
	defer cancel()
	return wait(ctx, name, time.Second, check)
}

func wait(ctx context.Context, name string, interval time.Duration, check func(context.Context) error) error {
	var last error
	for attempt := 1; ; attempt++ {
		if err := ctx.Err(); err != nil {
			return fmt.Errorf("%s startup: %w", name, errors.Join(err, last))
		}
		probe, cancel := context.WithTimeout(ctx, 10*time.Second)
		last = check(probe)
		cancel()
		if last == nil && ctx.Err() == nil {
			return nil
		}
		if attempt == 1 || attempt%10 == 0 {
			// Labels only: connection errors may contain credentials or upstream payloads.
			log.Printf("%s not ready; waiting for startup (attempt %d)", name, attempt)
		}
		timer := time.NewTimer(interval)
		select {
		case <-ctx.Done():
			timer.Stop()
			return fmt.Errorf("%s startup: %w", name, errors.Join(ctx.Err(), last))
		case <-timer.C:
		}
	}
}
