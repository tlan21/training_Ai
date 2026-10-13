import { useState } from "react";
import { useCmsUsers, useUpdateRole } from "../hooks/useCms";
import { useAuthStore } from "../stores/authStore";

export default function UsersPage() {
  const [page] = useState(1);
  const list = useCmsUsers(page);
  const upd = useUpdateRole();
  const meId = useAuthStore((s) => s.user?.id);
  const items: any[] = list.data?.items ?? list.data ?? [];
  return (
    <div>
      <h2>Người dùng (admin only)</h2>
      <div className="card" style={{ marginTop: 16, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr style={{ background: "var(--bg-surface-2)", textAlign: "left" }}><th style={{ padding: 8 }}>Username</th><th>Email</th><th>Role</th><th>Hành động</th></tr></thead>
          <tbody>
            {items.map((u: any) => (
              <tr key={u.id} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: 8 }}>{u.username}</td>
                <td>{u.email}</td>
                <td>
                  <select className="input" defaultValue={u.role} id={`role-${u.id}`} disabled={u.id === meId} style={{ padding: "4px 8px" }}>
                    <option value="admin">admin</option>
                    <option value="editor">editor</option>
                    <option value="client">client</option>
                  </select>
                </td>
                <td>
                  <button disabled={u.id === meId} onClick={() => {
                    const el = document.getElementById(`role-${u.id}`) as HTMLSelectElement;
                    if (el) upd.mutate({ id: u.id, role: el.value });
                  }} style={{ color: u.id === meId ? "var(--text-muted)" : "var(--primary)" }}>
                    Lưu
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div style={{ padding: 16, color: "var(--text-muted)" }}>{list.isLoading ? "Đang tải…" : "Không có user"}</div>}
      </div>
    </div>
  );
}
