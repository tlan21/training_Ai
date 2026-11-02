import { useEffect, useState } from "react";
import { Link, useBlocker } from "react-router-dom";
import type { components } from "../api-types";
import { useSettings, useUpdateSettings } from "../hooks/useCms";
import { useToast } from "../components/common/Toast";
import { Icon } from "../components/common/Icon";
import { Skeleton, ErrorState } from "../components/common/Skeleton";
import { useSystemHealth } from "../hooks/useAuth";
import { apiClient, errorMessage } from "../lib/apiClient";

export default function SettingsPage() {
  const settings = useSettings();
  const update = useUpdateSettings();
 const health=useSystemHealth({include_metrics:true});
  const toast = useToast();
  const [autoHighlight, setAutoHighlight] = useState(true);
  const [autoSubtitle, setAutoSubtitle] = useState(true);
  const reset = () => { setAutoHighlight(settings.data?.auto_highlight_enabled ?? true); setAutoSubtitle(settings.data?.auto_subtitle_enabled ?? true); };
const dirty=!!settings.data && (autoHighlight!==settings.data.auto_highlight_enabled || autoSubtitle!==settings.data.auto_subtitle_enabled);
 const blocker=useBlocker(dirty && !update.isPending);
 useEffect(()=>{if(blocker.state==="blocked"){if(confirm("Cài đặt chưa lưu. Rời trang?")) blocker.proceed(); else blocker.reset();}},[blocker]);
 useEffect(()=>{const handle=(event:BeforeUnloadEvent)=>{if(dirty){event.preventDefault();event.returnValue="";}};window.addEventListener("beforeunload",handle);return()=>window.removeEventListener("beforeunload",handle);},[dirty]);
 useEffect(reset, [settings.data]);
  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    const body: components["schemas"]["SettingsUpdate"] = { auto_highlight_enabled: autoHighlight, auto_subtitle_enabled: autoSubtitle };
    try {
      await update.mutateAsync(body);
      const { data } = await apiClient.get<components["schemas"]["Settings"]>("/api/cms/settings");
      if (data.auto_highlight_enabled !== body.auto_highlight_enabled || data.auto_subtitle_enabled !== body.auto_subtitle_enabled) toast.err("Máy chủ chưa lưu được cài đặt. Giá trị đã được tải lại.");
      else toast.ok("Đã lưu cài đặt");
    } catch (error) { toast.err(errorMessage(error)); }
  };
  return <div className="settings-page"><header className="settings-heading"><h3><Icon name="stitch_brand" color="var(--primary)" />Cài đặt</h3><div className="row-actions"><Link className="icon-button" to="/queue?status=failed" aria-label="Thông báo hệ thống"><Icon name="notifications" /></Link><Link className="icon-button" to="/users" aria-label="Quản lý người dùng"><Icon name="person" /></Link></div></header>
    <div className="tabs settings-tabs" role="tablist" aria-label="Cài đặt">{["Cài đặt chung", "Cấu hình AI", "Thông báo", "Bảo mật"].map((label) => <button key={label} role="tab" aria-selected={label === "Cấu hình AI"} disabled={label !== "Cấu hình AI"} title={label === "Cấu hình AI" ? undefined : "Chưa hỗ trợ cấu hình mục này"}>{label}</button>)}</div>
    {settings.isLoading ? <div className="settings-form"><Skeleton h={80} /><Skeleton h={80} /><Skeleton h={160} /></div> : settings.isError ? <ErrorState msg={errorMessage(settings.error)} onRetry={() => settings.refetch()} /> : <><form className="settings-form" onSubmit={save}>
      <section><h3>Tính năng AI</h3><ToggleCard icon="magic_button" title="Tự động đánh dấu (Auto-highlighting)" description="Tự động nhận diện các đoạn quan trọng bằng phân tích đa phương thức." checked={autoHighlight} onChange={setAutoHighlight} /><ToggleCard icon="closed_caption" title="Tạo phụ đề tự động" description="Bật tính năng tạo phụ đề tiếng Việt cho video." checked={autoSubtitle} onChange={setAutoSubtitle} /><div className="field"><label htmlFor="subtitle-language">Ngôn ngữ phụ đề mặc định</label><div className="input-wrap"><select id="subtitle-language" className="input input--with-right-icon" defaultValue="vi" disabled><option value="vi">Tiếng Việt</option></select><span className="input-icon input-icon--right"><Icon name="expand_more" /></span></div></div></section>
      <section><div className="threshold-heading"><h3>Ngưỡng gợi ý AI</h3><span className="badge">Theo model</span></div><div className="threshold-card"><p>Ngưỡng được AI xác định cho từng kết quả và hiển thị tại màn Highlight. Không điều chỉnh tại đây; thay đổi cài đặt không tính lại các clip đã tạo.</p></div></section>
      <section><h3>Kết nối & Lưu trữ</h3><div className="settings-connection"><div className="field"><label htmlFor="ai-service-key"><Icon name="key" size={16} />AI Service API Key</label><input id="ai-service-key" className="input" type="password" value={settings.data?.ai_service_api_key ?? "sk-local-••••"} readOnly title="Key được cấu hình trên máy chủ" /></div><div className="field"><label htmlFor="storage-provider"><Icon name="cloud" size={16} />Storage Provider</label><div className="input-wrap"><select id="storage-provider" className="input input--with-right-icon" disabled defaultValue="MinIO"><option>MinIO</option></select><span className="input-icon input-icon--right"><Icon name="expand_more" /></span></div></div></div><div className="field"><label htmlFor="storage-buckets">S3 Bucket Name</label><input id="storage-buckets" className="input" value={health.data?.storage?.buckets.map(bucket=>bucket.name).join(" / ") ?? "Chưa đọc được bucket"} readOnly /></div></section>
      {health.data?.storage_error && <p className="error-text" role="status">{health.data.storage_error}</p>}<p className="micro">Cấu hình áp dụng cho video tải lên sau khi lưu. Retry giữ cấu hình của lần tải ban đầu; tắt phụ đề cũng bỏ bước tóm tắt.</p><div className="settings-submit"><button type="button" className="btn-text" onClick={reset} disabled={update.isPending}>Hủy bỏ</button><button className="btn-primary" disabled={update.isPending || !dirty}><Icon name="save" size={20} />{update.isPending ? "Đang lưu…" : "Lưu thay đổi"}</button></div>

    </form><div className="settings-atmosphere"><h4>Tối ưu hiệu suất</h4><p>Cấu hình AI áp dụng cho quá trình xử lý video.</p></div></>}
  </div>;
}
function ToggleCard({ icon, title, description, checked, onChange }: { icon: string; title: string; description: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <div className="toggle-card"><span className="toggle-icon"><Icon name={icon} /></span><div className="min-zero"><strong>{title}</strong><p>{description}</p></div><label className="switch"><span /><input type="checkbox" aria-label={title} checked={checked} onChange={(event) => onChange(event.target.checked)} /></label></div>;
}
