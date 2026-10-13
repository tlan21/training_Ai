import { useEffect, useState } from "react";
import { useSettings, useUpdateSettings } from "../hooks/useCms";

export default function SettingsPage() {
  const { data } = useSettings();
  const upd = useUpdateSettings();
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
  const save = () => upd.mutate({ highlight_threshold: thr, asr_warning_threshold: asr, auto_highlight_enabled: autoHl, auto_subtitle_enabled: autoSub, ai_service_api_key: key || undefined });
  return (
    <div>
      <h2>Cài đặt — Cấu hình AI</h2>
      <div className="card" style={{ padding: 16, marginTop: 16, display: "grid", gap: 16, maxWidth: 520 }}>
        <label style={{ display: "flex", justifyContent: "space-between" }}><span>Tự động đánh dấu highlight</span><input type="checkbox" checked={autoHl} onChange={(e) => setAutoHl(e.target.checked)} /></label>
        <label style={{ display: "flex", justifyContent: "space-between" }}><span>Tạo phụ đề tự động</span><input type="checkbox" checked={autoSub} onChange={(e) => setAutoSub(e.target.checked)} /></label>
        <label>Ngưỡng gợi ý AI: {thr}<input type="range" min={0} max={100} value={thr} onChange={(e) => setThr(Number(e.target.value))} style={{ width: "100%" }} /></label>
        <label>Ngưỡng cảnh báo ASR: {asr}<input type="range" min={0} max={100} value={asr} onChange={(e) => setAsr(Number(e.target.value))} style={{ width: "100%" }} /></label>
        <label>Ngôn ngữ phụ đề
          <select className="input" style={{ width: "100%", marginTop: 4 }} defaultValue="vi">
            <option value="vi">Tiếng Việt</option>
          </select>
        </label>
        <label>AI Service API Key (masked: {data?.ai_service_api_key ?? "sk-local-••••"})
          <input className="input" type="password" placeholder="sk-local-..." value={key} onChange={(e) => setKey(e.target.value)} style={{ width: "100%", marginTop: 4 }} />
        </label>
        <button className="btn-primary" onClick={save} disabled={upd.isPending}>{upd.isPending ? "Đang lưu…" : "Lưu cài đặt"}</button>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Storage: MinIO (read-only)</div>
      </div>
    </div>
  );
}
