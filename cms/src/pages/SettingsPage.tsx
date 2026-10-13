import { useEffect, useState } from "react";
import { useSettings, useUpdateSettings } from "../hooks/useCms";
import { useToast } from "../components/common/Toast";

export default function SettingsPage() {
  const { data } = useSettings();
  const upd = useUpdateSettings();
  const toast = useToast();
  const [tab, setTab] = useState<"general" | "ai" | "notify" | "security">("ai");
  const [thr, setThr] = useState(75);
  const [asr, setAsr] = useState(65);
  const [autoHl, setAutoHl] = useState(true);
  const [autoSub, setAutoSub] = useState(true);
  const [key, setKey] = useState("");
  useEffect(() => {
    if (data) {
      setThr(data.highlight_threshold ?? 75);
      setAsr(data.asr_warning_threshold ?? 65);
      setAutoHl(data.auto_highlight_enabled ?? true);
      setAutoSub(data.auto_subtitle_enabled ?? true);
    }
  }, [data]);
  const save = () => upd.mutate(
    { highlight_threshold: thr, asr_warning_threshold: asr, auto_highlight_enabled: autoHl, auto_subtitle_enabled: autoSub, ai_service_api_key: key || undefined },
    { onSuccess: () => toast.ok("Đã lưu cài đặt"), onError: (e: any) => toast.err(e?.apiError?.message ?? e.message) },
  );
  return (
    <div>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--outline-variant)", padding: "12px 0", marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Cài đặt</h2>
      </header>
      <div style={{ display: "flex", borderBottom: "1px solid var(--outline-variant)", gap: 24, overflowX: "auto" }}>
        {[
          ["general", "Cài đặt chung"],
          ["ai", "Cấu hình AI"],
          ["notify", "Thông báo"],
          ["security", "Bảo mật"],
        ].map(([id, label]) => (
          <button key={id} onClick={() => setTab(id as any)} style={{ padding: "12px 0 13px", borderBottom: tab === id ? "3px solid var(--primary-container)" : "3px solid transparent", color: tab === id ? "var(--on-surface)" : "var(--on-surface-variant)", fontWeight: 700, fontSize: 13, background: "none", borderTop: "none", borderLeft: "none", borderRight: "none", cursor: "pointer", whiteSpace: "nowrap" }}>
            {label}
          </button>
        ))}
      </div>

      {tab !== "ai" && <div style={{ padding: 32, textAlign: "center", color: "var(--on-surface-variant)" }}>{tab === "general" ? "Cài đặt chung — sắp ra mắt" : tab === "notify" ? "Thông báo — sắp ra mắt" : "Bảo mật — sắp ra mắt"}</div>}

      {tab === "ai" && (
        <div style={{ maxWidth: 720, margin: "0 auto", display: "grid", gap: 24, padding: "24px 0" }}>
          <section style={{ display: "grid", gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Tính năng AI</h3>
            <ToggleCard icon="magic_button" title="Tự động đánh dấu (Auto-highlighting)" desc="Tự động nhận diện các đoạn quan trọng bằng Vision+Audio fusion." checked={autoHl} onChange={setAutoHl} />
            <ToggleCard icon="closed_caption" title="Tạo phụ đề tự động" desc="Bật tính năng tạo phụ đề tiếng Việt (ASR) cho video." checked={autoSub} onChange={setAutoSub} />
            <div style={{ display: "grid", gap: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--on-surface-variant)" }}>Ngôn ngữ phụ đề mặc định</label>
              <div style={{ position: "relative" }}>
                <select className="input" style={{ width: "100%", height: 44, appearance: "none" }} defaultValue="vi" disabled>
                  <option value="vi">Tiếng Việt</option>
                </select>
                <span className="material-symbols-outlined" style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", color: "var(--on-surface-variant)", pointerEvents: "none" }}>expand_more</span>
              </div>
              <span style={{ fontSize: 11, color: "var(--on-surface-variant)" }}>ASR chỉ huấn luyện tiếng Việt — các ngôn ngữ khác đã ẩn theo CẮT-list.</span>
            </div>
          </section>

          <section style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Ngưỡng gợi ý AI</h3>
              <span style={{ background: "var(--primary-fixed)", color: "var(--primary)", fontWeight: 700, fontSize: 12, padding: "4px 10px", borderRadius: 9999 }}>{thr}%</span>
            </div>
            <div style={{ background: "var(--surface-container-low)", padding: 20, borderRadius: 12, border: "1px solid rgba(203,195,213,0.3)" }}>
              <p style={{ fontSize: 13, color: "var(--on-surface-variant)", margin: "0 0 12px" }}>Điều chỉnh độ nhạy khi đề xuất đoạn cắt. Giá trị cao hơn cho kết quả ít hơn nhưng chính xác hơn. Heatmap vùng đỏ và gom clip dùng ngưỡng này.</p>
              <input type="range" min={0} max={100} value={thr} onChange={(e) => setThr(Number(e.target.value))} style={{ width: "100%", accentColor: "var(--primary-container)", height: 6 }} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontWeight: 700, color: "var(--outline)", marginTop: 6, letterSpacing: 1, textTransform: "uppercase" }}><span>Chính xác thấp</span><span>Chính xác cao</span></div>
              <label style={{ display: "block", marginTop: 12, fontSize: 12, fontWeight: 600 }}>Ngưỡng cảnh báo ASR: {asr}%<input type="range" min={0} max={100} value={asr} onChange={(e) => setAsr(Number(e.target.value))} style={{ width: "100%", accentColor: "var(--primary-container)" }} /></label>
            </div>
          </section>

          <section style={{ display: "grid", gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Kết nối & Lưu trữ</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={{ display: "grid", gap: 6 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--on-surface-variant)", display: "flex", gap: 6, alignItems: "center" }}><span className="material-symbols-outlined" style={{ fontSize: 14 }}>key</span> AI Service API Key</label>
                <input className="input" type="password" placeholder="sk-local-••••" value={key} onChange={(e) => setKey(e.target.value)} style={{ height: 44 }} />
                <span style={{ fontSize: 11, color: "var(--on-surface-variant)" }}>Đang lưu: {data?.ai_service_api_key ?? "sk-local-••••"} (masked) — key của inference-service :8001 tự dựng.</span>
              </div>
              <div style={{ display: "grid", gap: 6 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--on-surface-variant)", display: "flex", gap: 6, alignItems: "center" }}><span className="material-symbols-outlined" style={{ fontSize: 14 }}>cloud</span> Storage Provider</label>
                <div style={{ position: "relative" }}>
                  <select className="input" style={{ width: "100%", height: 44, appearance: "none" }} defaultValue="MinIO" disabled>
                    <option>MinIO</option>
                  </select>
                  <span className="material-symbols-outlined" style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}>expand_more</span>
                </div>
                <span style={{ fontSize: 11, color: "var(--on-surface-variant)" }}>Chỉ MinIO — read-only (CẮT-list: bỏ AWS/GCS/Azure).</span>
              </div>
            </div>
            <div style={{ display: "grid", gap: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--on-surface-variant)" }}>S3 Bucket Name</label>
              <input className="input" placeholder="videos / milvus" disabled style={{ height: 44 }} />
            </div>
          </section>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, borderTop: "1px solid var(--outline-variant)", paddingTop: 16, marginTop: 8 }}>
            <button onClick={() => window.location.reload()} style={{ padding: "10px 20px", borderRadius: 9999, border: "none", background: "transparent", color: "var(--on-surface-variant)", fontWeight: 700, cursor: "pointer" }}>Hủy bỏ</button>
            <button className="btn-primary" onClick={save} disabled={upd.isPending} style={{ padding: "10px 28px", borderRadius: 9999, display: "flex", gap: 8, alignItems: "center" }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>save</span> {upd.isPending ? "Đang lưu..." : "Lưu thay đổi"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ToggleCard({ icon, title, desc, checked, onChange }: { icon: string; title: string; desc: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, background: "var(--surface-container-low)", borderRadius: 12, padding: "12px 16px", border: "1px solid rgba(203,195,213,0.3)", justifyContent: "space-between" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <div style={{ width: 44, height: 44, borderRadius: 8, background: "var(--surface-container-highest)", display: "grid", placeItems: "center", flexShrink: 0 }}>
          <span className="material-symbols-outlined">{icon}</span>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{title}</div>
          <div style={{ fontSize: 12, color: "var(--on-surface-variant)" }}>{desc}</div>
        </div>
      </div>
      <label style={{ position: "relative", width: 51, height: 31, borderRadius: 9999, background: checked ? "var(--primary-container)" : "var(--outline-variant)", display: "flex", alignItems: "center", padding: 2, cursor: "pointer", flexShrink: 0, transition: "background 0.2s" }}>
        <div style={{ width: 27, height: 27, borderRadius: 9999, background: "white", boxShadow: "0 1px 4px rgba(0,0,0,0.2)", transform: checked ? "translateX(20px)" : "translateX(0)", transition: "transform 0.2s" }} />
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} style={{ position: "absolute", opacity: 0, pointerEvents: "none" }} />
      </label>
    </div>
  );
}
