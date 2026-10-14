import { statusMap } from "../../lib/statusMap";
export function StatusBadge({ status }: { status: string }) {
  const m = statusMap[status] ?? { color: "var(--text-muted)", label: status };
  return (
    <span className="badge" style={{ background: `color-mix(in srgb, ${m.color} 12%, transparent)`, color: m.color, border: `1px solid color-mix(in srgb, ${m.color} 25%, transparent)` }}>
      {m.label}
    </span>
  );
}
