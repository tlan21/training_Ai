import { useState } from "react";
import { useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory } from "../hooks/useCms";

export default function CategoriesPage() {
  const list = useCategories();
  const create = useCreateCategory();
  const upd = useUpdateCategory();
  const del = useDeleteCategory();
  const [name, setName] = useState("");
  const [edit, setEdit] = useState<{ id: string; name: string } | null>(null);
  const items: any[] = list.data ?? [];
  return (
    <div>
      <h2>Danh mục</h2>
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input className="input" placeholder="Tên danh mục" value={name} onChange={(e) => setName(e.target.value)} />
        <button className="btn-primary" onClick={async () => { if (!name) return; await create.mutateAsync({ name }); setName(""); }}>+ Thêm</button>
      </div>
      <div className="card" style={{ marginTop: 16, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr style={{ background: "var(--bg-surface-2)", textAlign: "left" }}><th style={{ padding: 8 }}>Tên</th><th>Hành động</th></tr></thead>
          <tbody>
            {items.map((c: any) => (
              <tr key={c.id} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: 8 }}>{c.name}</td>
                <td style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => setEdit(c)} style={{ color: "var(--primary)" }}>Sửa</button>
                  <button onClick={() => { if (confirm("Xóa danh mục?")) del.mutate(c.id); }} style={{ color: "var(--danger)" }}>Xóa</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {edit && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "grid", placeItems: "center" }} onClick={() => setEdit(null)}>
          <div className="card" style={{ padding: 16, width: 360 }} onClick={(e) => e.stopPropagation()}>
            <h3>Sửa danh mục</h3>
            <input className="input" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} style={{ width: "100%", marginTop: 8 }} />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="btn-primary" onClick={async () => { await upd.mutateAsync({ id: edit.id, name: edit.name }); setEdit(null); }}>Lưu</button>
              <button onClick={() => setEdit(null)}>Hủy</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
