export function Skeleton({ h = 14, w = "100%" }: { h?: number; w?: string | number }) {
  return <div style={{ height: h, width: w, background: "var(--bg-surface-2)", borderRadius: 6, animation: "pulse 1.2s infinite" }} />;
}
export function Empty({ msg }: { msg: string }) {
  return <div style={{ padding: 16, color: "var(--text-muted)", textAlign: "center", fontSize: 13 }}>{msg}</div>;
}
export function ErrorState({ msg, onRetry }: { msg: string; onRetry?: () => void }) {
  return (
    <div style={{ padding: 16, color: "var(--danger)", textAlign: "center", fontSize: 13 }}>
      {msg} {onRetry && <button onClick={onRetry} style={{ marginLeft: 8, color: "var(--primary)" }}>Thử lại</button>}
    </div>
  );
}
