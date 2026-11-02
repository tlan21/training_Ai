import { statusMap } from "../../lib/statusMap";
import { Icon } from "./Icon";
// INT-05: Stitch draws status differently per screen — caps (Dashboard table), pill (Videos), text (Library); default = tinted badge.
const done = new Set(["processed", "published", "completed"]);
const bad = new Set(["failed", "rejected"]);
export function StatusBadge({ status, variant }: { status: string; variant?: "caps" | "pill" | "text" }) {
  const m = statusMap[status] ?? { color: "var(--text-muted)", label: status };
  const tone = done.has(status) ? "done" : bad.has(status) ? "bad" : "busy";
  if (variant === "caps") return <span className={`status-caps is-${tone}`}>{m.label}</span>;
  if (variant === "pill") return tone === "bad" ? <span className="status-pill is-bad"><Icon name="error" size={14} />{m.label}</span> : <span className={`status-pill is-${tone}`}><span className="status-dot" />{m.label}</span>;
  if (variant === "text") return <span className={`status-text is-${tone}`}><span className="status-dot" />{m.label}</span>;
  return (
    <span className="badge" style={{ background: `color-mix(in srgb, ${m.color} 12%, transparent)`, color: m.color, border: `1px solid color-mix(in srgb, ${m.color} 25%, transparent)` }}>
      {m.label}
    </span>
  );
}
