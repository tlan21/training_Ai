import { useState } from "react";
import { useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory } from "../hooks/useCms";
import { useToast } from "../components/common/Toast";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";

const iconMap: Record<string, string> = {
  "Bóng đá": "sports_soccer", "Thể thao": "sports_soccer", "Game": "sports_esports",
  "Ca nhạc": "music_note", "Tin tức": "newspaper", "Giải trí": "movie", "Highlight": "auto_awesome",
  "Giáo dục": "school", "Du lịch": "flight", "Ẩm thực": "restaurant", "Công nghệ": "memory",
};

export default function CategoriesPage() {
  const list = useCategories();
  const create = useCreateCategory();
  const upd = useUpdateCategory();
  const del = useDeleteCategory();
  const toast = useToast();
  const [name, setName] = useState("");
  const [edit, setEdit] = useState<{ id: string; name: string } | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const items: any[] = list.data ?? [];

  const doCreate = async () => {
    if (!name.trim()) return;
    try { await create.mutateAsync({ name: name.trim() }); setName(""); setCreateOpen(false); toast.ok("Đã tạo danh mục"); }
    catch (e: any) { toast.err(e?.apiError?.message ?? e.message); }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", marginBottom: 8 }}>
        <div>
          <nav style={{ display: "flex", gap: 6, fontSize: 11, color: "var(--outline)", marginBottom: 4 }}>
            <span>CMS</span><span className="material-symbols-outlined" style={{ fontSize: 12 }}>chevron_right</span><span style={{ color: "var(--primary)", fontWeight: 700 }}>Quản lý Danh mục</span>
          </nav>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Quản lý Danh mục</h2>
          <p style={{ color: "var(--on-surface-variant)", fontSize: 13, margin: "4px 0 0" }}>Phân loại và cấu hình quy tắc gán tự động cho kho nội dung video.</p>
        </div>
        <button onClick={() => setCreateOpen(true)} style={{ display: "flex", gap: 6, alignItems: "center", padding: "10px 18px", background: "var(--primary)", color: "var(--on-primary)", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span> Thêm danh mục mới
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 16, alignItems: "start" }}>
        <div>
          {list.isLoading && <div style={{ display: "grid", gap: 8 }}><Skeleton h={44} /><Skeleton h={44} /><Skeleton h={44} /></div>}
          {list.isError && <ErrorState msg={(list.error as any)?.apiError?.message ?? "Lỗi tải danh mục"} onRetry={() => list.refetch()} />}
          {!list.isLoading && !list.isError && (
            <div style={{ background: "var(--surface-container-lowest)", border: "1px solid var(--outline-variant)", borderRadius: 12, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-container-low)", borderBottom: "1px solid var(--outline-variant)", textAlign: "left" }}>
                    <th style={{ padding: "8px 12px", fontSize: 10, color: "var(--outline)", letterSpacing: 1, textTransform: "uppercase", width: 56, textAlign: "center" }}>Icon</th>
                    <th style={{ padding: "8px 12px", fontSize: 10, color: "var(--outline)", letterSpacing: 1, textTransform: "uppercase" }}>Tên danh mục</th>
                    <th style={{ padding: "8px 12px", fontSize: 10, color: "var(--outline)", letterSpacing: 1, textTransform: "uppercase" }}>Mô tả</th>
                    <th style={{ padding: "8px 12px", fontSize: 10, color: "var(--outline)", letterSpacing: 1, textTransform: "uppercase", textAlign: "center" }}>Video</th>
                    <th style={{ padding: "8px 12px", fontSize: 10, color: "var(--outline)", letterSpacing: 1, textTransform: "uppercase" }}>Quy tắc</th>
                    <th style={{ padding: "8px 12px", fontSize: 10, color: "var(--outline)", letterSpacing: 1, textTransform: "uppercase" }}>Trạng thái</th>
                    <th style={{ padding: "8px 12px", fontSize: 10, color: "var(--outline)", letterSpacing: 1, textTransform: "uppercase", textAlign: "right" }}>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((c: any) => {
                    const isSystem = c.name === "Highlight";
                    return (
                      <tr key={c.id} style={{ borderTop: "1px solid var(--outline-variant)" }} className="hover-row">
                        <td style={{ padding: "10px 12px", textAlign: "center" }}>
                          <div style={{ width: 36, height: 36, margin: "0 auto", borderRadius: 8, background: isSystem ? "rgba(70,21,153,0.12)" : "var(--surface-container)", color: isSystem ? "var(--primary)" : "var(--on-surface-variant)", display: "grid", placeItems: "center" }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>{iconMap[c.name] ?? "category"}</span>
                          </div>
                        </td>
                        <td style={{ padding: "10px 12px" }}>
                          <div style={{ fontWeight: 600, color: isSystem ? "var(--primary)" : "var(--on-surface)", fontSize: 13 }}>{c.name}</div>
                          {isSystem && <span style={{ fontSize: 9, fontWeight: 700, background: "var(--secondary-container)", color: "var(--on-secondary-container)", padding: "2px 6px", borderRadius: 4, marginTop: 4, display: "inline-block" }}>HỆ THỐNG</span>}
                        </td>
                        <td style={{ padding: "10px 12px", maxWidth: 180, color: "var(--on-surface-variant)", fontSize: 12 }}>{isSystem ? "Danh mục mặc định cho clip cắt tự động bởi AI." : "—"}</td>
                        <td style={{ padding: "10px 12px", textAlign: "center", fontFamily: "JetBrains Mono", fontSize: 12 }}>—</td>
                        <td style={{ padding: "10px 12px", fontSize: 12 }}>{isSystem ? <span style={{ display: "flex", gap: 4, alignItems: "center", color: "var(--primary)", fontWeight: 600 }}><span className="material-symbols-outlined" style={{ fontSize: 12 }}>bolt</span> Tự động (Khóa)</span> : <span style={{ color: "var(--outline)" }}>Thủ công</span>}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <span style={{ display: "inline-flex", gap: 6, alignItems: "center", padding: "2px 8px", borderRadius: 9999, fontSize: 11, background: "var(--secondary-container)", color: "var(--secondary-fixed-dim)" !== undefined ? "var(--on-secondary-fixed)" : "var(--on-secondary-container)", backgroundColor: "var(--secondary-container)" as any }}>
                            <span style={{ width: 6, height: 6, borderRadius: 9999, background: "var(--on-secondary-fixed)", display: "inline-block" }} /> Đã duyệt
                          </span>
                        </td>
                        <td style={{ padding: "10px 12px", textAlign: "right" }}>
                          <div style={{ display: "flex", justifyContent: "end", gap: 4 }}>
                            {!isSystem ? (
                              <>
                                <button onClick={() => setEdit(c)} style={{ padding: 6, color: "var(--outline)", background: "none", border: "none", cursor: "pointer" }} title="Sửa"><span className="material-symbols-outlined" style={{ fontSize: 18 }}>edit</span></button>
                                <button onClick={() => { if (confirm(`Xóa danh mục "${c.name}"?`)) del.mutate(c.id, { onSuccess: () => toast.ok("Đã xóa"), onError: (e: any) => toast.err(e?.apiError?.message ?? e.message) }); }} style={{ padding: 6, color: "var(--outline)", background: "none", border: "none", cursor: "pointer" }} title="Xóa"><span className="material-symbols-outlined" style={{ fontSize: 18 }}>delete</span></button>
                              </>
                            ) : (
                              <>
                                <button style={{ padding: 6, color: "var(--outline)", background: "none", border: "none" }} title="Xem"><span className="material-symbols-outlined" style={{ fontSize: 18 }}>visibility</span></button>
                                <button style={{ padding: 6, color: "var(--outline)", background: "none", border: "none" }} title="Cài đặt"><span className="material-symbols-outlined" style={{ fontSize: 18 }}>settings</span></button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {items.length === 0 && <Empty msg="Chưa có danh mục" />}
            </div>
          )}
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          <section style={{ background: "var(--surface-container-lowest)", border: "1px solid var(--outline-variant)", borderRadius: 12, padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, display: "flex", gap: 6, alignItems: "center" }}><span className="material-symbols-outlined" style={{ color: "var(--primary)", fontSize: 16 }}>circle</span> Cấu hình Tự động gán AI</h3>
              <button style={{ color: "var(--primary)", fontSize: 11, fontWeight: 700, background: "none", border: "none", cursor: "pointer" }}>Chỉnh sửa</button>
            </div>
            <div style={{ background: "rgba(70,21,153,0.06)", border: "1px solid rgba(70,21,153,0.15)", borderRadius: 8, padding: 12, display: "flex", gap: 12, marginBottom: 12 }}>
              <div style={{ width: 36, height: 36, borderRadius: 9999, background: "var(--primary-container)", color: "var(--on-primary-container)", display: "grid", placeItems: "center", flexShrink: 0 }}><span className="material-symbols-outlined" style={{ fontSize: 16 }}>lock</span></div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 13, color: "var(--primary)" }}>Danh mục Highlight AI</div>
                <div style={{ fontSize: 12, color: "var(--on-surface-variant)", marginTop: 4 }}>Hệ thống luôn tự động gán video từ Highlight AI vào danh mục này. Không thể tắt.</div>
              </div>
            </div>
            <label style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", cursor: "pointer" }}>
              <span style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}><span className="material-symbols-outlined" style={{ fontSize: 16, color: "var(--outline)" }}>tag</span> Gán theo từ khóa AI</span>
              <span style={{ width: 40, height: 20, borderRadius: 9999, background: "var(--primary)", position: "relative", display: "inline-block" }}><span style={{ position: "absolute", right: 2, top: 2, width: 16, height: 16, borderRadius: 9999, background: "white" }} /></span>
            </label>
            <label style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", cursor: "pointer", opacity: 0.7 }}>
              <span style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}><span className="material-symbols-outlined" style={{ fontSize: 16, color: "var(--outline)" }}>face</span> Nhận diện nhân vật</span>
              <span style={{ width: 40, height: 20, borderRadius: 9999, background: "var(--outline-variant)", position: "relative", display: "inline-block" }}><span style={{ position: "absolute", left: 2, top: 2, width: 16, height: 16, borderRadius: 9999, background: "white" }} /></span>
            </label>
            <div style={{ fontSize: 11, color: "var(--on-surface-variant)", marginTop: 8 }}>Đã ẩn theo CẮT-list: chỉ hiển thị, không thao tác.</div>
          </section>

          <section style={{ background: "var(--surface-container-lowest)", border: "1px solid var(--outline-variant)", borderRadius: 12, overflow: "hidden" }}>
            <div style={{ padding: 12, borderBottom: "1px solid var(--outline-variant)", display: "flex", justifyContent: "space-between" }}>
              <h3 style={{ margin: 0, fontSize: 13, fontWeight: 700 }}>Gán video gần đây</h3>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: "var(--outline)", cursor: "pointer" }}>refresh</span>
            </div>
            <div style={{ padding: 8, display: "grid", gap: 6, maxHeight: 280, overflowY: "auto" }}>
              <div style={{ fontSize: 12, color: "var(--on-surface-variant)", padding: 8 }}>Cần video thật để hiện — đang dùng mem-mock.</div>
            </div>
            <div style={{ padding: 12, borderTop: "1px solid var(--outline-variant)", textAlign: "center" }}>
              <button style={{ color: "var(--primary)", fontSize: 13, fontWeight: 600, background: "none", border: "none", cursor: "pointer" }}>Xem tất cả video</button>
            </div>
          </section>
        </div>
      </div>

      {createOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "grid", placeItems: "center", zIndex: 50 }} onClick={() => setCreateOpen(false)}>
          <div style={{ background: "var(--surface-container-lowest)", borderRadius: 12, padding: 20, width: 400 }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 12px" }}>Thêm danh mục mới</h3>
            <input className="input" placeholder="Tên danh mục" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doCreate()} style={{ width: "100%" }} autoFocus />
            <div style={{ display: "flex", gap: 8, justifyContent: "end", marginTop: 16 }}>
              <button onClick={() => setCreateOpen(false)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--outline-variant)", background: "white", cursor: "pointer" }}>Hủy</button>
              <button className="btn-primary" onClick={doCreate} disabled={create.isPending}>{create.isPending ? "Đang tạo..." : "Tạo"}</button>
            </div>
          </div>
        </div>
      )}

      {edit && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "grid", placeItems: "center", zIndex: 50 }} onClick={() => setEdit(null)}>
          <div style={{ background: "var(--surface-container-lowest)", borderRadius: 12, padding: 20, width: 360 }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 12px" }}>Sửa danh mục</h3>
            <input className="input" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} style={{ width: "100%" }} />
            <div style={{ display: "flex", gap: 8, justifyContent: "end", marginTop: 16 }}>
              <button onClick={() => setEdit(null)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--outline-variant)", background: "white", cursor: "pointer" }}>Hủy</button>
              <button className="btn-primary" onClick={async () => { try { await upd.mutateAsync({ id: edit.id, name: edit.name }); setEdit(null); toast.ok("Đã cập nhật"); } catch (e: any) { toast.err(e?.apiError?.message ?? e.message); } }}>Lưu</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
