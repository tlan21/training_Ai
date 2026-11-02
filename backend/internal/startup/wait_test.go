package startup

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestWaitRecoversAndStopsProbing(t *testing.T) {
	calls := 0
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	err := wait(ctx, "fixture", time.Millisecond, func(probe context.Context) error {
		if _, ok := probe.Deadline(); !ok {
			t.Fatal("probe has no deadline")
		}
		calls++
		if calls < 3 {
			return errors.New("dependency starting")
		}
		return nil
	})
	if err != nil || calls != 3 {
		t.Fatalf("err=%v calls=%d", err, calls)
	}
}

func TestWaitDeadlineRetainsCause(t *testing.T) {
	cause := errors.New("not ready")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
	defer cancel()
	err := wait(ctx, "fixture", time.Millisecond, func(context.Context) error { return cause })
	if !errors.Is(err, context.DeadlineExceeded) || !errors.Is(err, cause) {
		t.Fatalf("lost deadline/cause: %v", err)
	}
}

func TestWaitCancellationAndBlockedProbe(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := Wait(ctx, "cancelled", func(context.Context) error { t.Fatal("probe after cancellation"); return nil }); !errors.Is(err, context.Canceled) {
		t.Fatal(err)
	}
	ctx, cancel = context.WithTimeout(context.Background(), 10*time.Millisecond)
	defer cancel()
	err := wait(ctx, "blocked", time.Millisecond, func(probe context.Context) error { <-probe.Done(); return probe.Err() })
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatal(err)
	}
}
