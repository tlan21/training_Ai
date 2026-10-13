import { statusMap } from "../../lib/statusMap";
export function StatusBadge({ status }: { status: string }) {
  const m = statusMap[status] ?? { color: "var(--text-muted)", label: status };
  return (
    <span className="badge" style={{ background: `${m.color}22`, color: m.color, border: `1px solid ${m.color}44` }}>
      {m.label}
    </span>
  );
}
