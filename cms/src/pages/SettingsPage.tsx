import { useEffect, useState } from "react";
import { Link, useBlocker, useSearchParams } from "react-router-dom";
import axios from "axios";
import type { components } from "../api-types";
import { useChangePassword, useRevokeOtherSessions, useSettings, useUpdateSettings } from "../hooks/useCms";
import { useToast } from "../components/common/Toast";
import { Icon } from "../components/common/Icon";
import { Skeleton, ErrorState } from "../components/common/Skeleton";
import { useAuthStore } from "../stores/authStore";
import { apiClient, errorMessage } from "../lib/apiClient";

type Settings = components["schemas"]["Settings"];
type Update = components["schemas"]["SettingsUpdate"];
type Tab = "general" | "ai" | "notifications" | "security";
const TABS: [Tab, string][] = [["general", "Cài đặt chung"], ["ai", "Cấu hình AI"], ["notifications", "Thông báo"], ["security", "Bảo mật"]];
const ZONES: [NonNullable<Settings["display_timezone"]>, string][] = [["Asia/Ho_Chi_Minh", "Việt Nam (GMT+7)"], ["Asia/Bangkok", "Bangkok (GMT+7)"], ["Asia/Singapore", "Singapore (GMT+8)"], ["Asia/Tokyo", "Tokyo (GMT+9)"], ["UTC", "UTC (GMT+0)"]];
// A changed group is sent whole (AI flags kept as before); untouched groups are never sent, so an editor saving AI flags never hits the admin-only 403.
const GROUPS = { ai: ["auto_highlight_enabled", "auto_subtitle_enabled"], general: ["system_name", "display_timezone"], notifications: ["notify_failed_jobs", "notify_uncategorized_videos"], session: ["session_ttl_days"] } as const;
type Key = (typeof GROUPS)[keyof typeof GROUPS][number];
type Draft = { [K in Key]: NonNullable<Settings[K]> };
const fromServer = (s?: Settings): Draft => ({
  auto_highlight_enabled: s?.auto_highlight_enabled ?? true, auto_subtitle_enabled: s?.auto_subtitle_enabled ?? true,
  system_name: s?.system_name ?? "AI Video CMS", display_timezone: s?.display_timezone ?? "Asia/Ho_Chi_Minh",
  notify_failed_jobs: s?.notify_failed_jobs ?? true, notify_uncategorized_videos: s?.notify_uncategorized_videos ?? true, session_ttl_days: s?.session_ttl_days ?? 7,
});
const norm = (key: Key, value: Draft[Key]) => (key === "system_name" ? String(value).trim() : value);
const apiCode = (error: unknown) => (axios.isAxiosError<components["schemas"]["Error"]>(error) ? error.response?.data?.error?.code : undefined);

export default function SettingsPage() {
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find(([key]) => key === params.get("tab"))?.[0] ?? "ai") as Tab;
  const isAdmin = useAuthStore((state) => state.user?.role) === "admin";
  const settings = useSettings();
  const update = useUpdateSettings();
  const toast = useToast();
  const [draft, setDraft] = useState<Draft>(fromServer());
  const server = fromServer(settings.data);
  const reset = () => setDraft(fromServer(settings.data));
  const set = <K extends Key>(key: K, value: Draft[K]) => setDraft((current) => ({ ...current, [key]: value }));
  const changed = (Object.keys(GROUPS) as (keyof typeof GROUPS)[]).filter((group) => GROUPS[group].some((key) => norm(key, draft[key]) !== norm(key, server[key])));
  const dirty = !!settings.data && changed.length > 0;
  const nameError = (() => { const n = [...draft.system_name.trim()].length; return n < 1 ? "Tên hệ thống không được để trống" : n > 60 ? "Tối đa 60 ký tự" : ""; })();
  const ttlError = Number.isInteger(draft.session_ttl_days) && draft.session_ttl_days >= 1 && draft.session_ttl_days <= 30 ? "" : "Nhập số ngày từ 1 đến 30";
  const invalid = (changed.includes("general") && !!nameError) || (changed.includes("session") && !!ttlError);
  const blocker = useBlocker(dirty && !update.isPending);
  useEffect(() => { if (blocker.state === "blocked") { if (confirm("Cài đặt chưa lưu. Rời trang?")) blocker.proceed(); else blocker.reset(); } }, [blocker]);
  useEffect(() => { const handle = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } }; window.addEventListener("beforeunload", handle); return () => window.removeEventListener("beforeunload", handle); }, [dirty]);
  useEffect(reset, [settings.data]);
  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (invalid) return;
    const body: Update = {};
    for (const group of changed) for (const key of GROUPS[group]) Object.assign(body, { [key]: norm(key, draft[key]) });
    try {
      await update.mutateAsync(body);
      const { data } = await apiClient.get<Settings>("/api/cms/settings");
      if (Object.entries(body).some(([key, value]) => data[key as Key] !== value)) toast.err("Máy chủ chưa lưu được cài đặt. Giá trị đã được tải lại.");
      else toast.ok("Đã lưu cài đặt");
    } catch (error) { toast.err(apiCode(error) === "FORBIDDEN" ? "Chỉ quản trị viên được thay đổi mục này" : errorMessage(error)); }
  };
  const adminNote = !isAdmin && <p className="settings-note" role="note"><Icon name="lock" size={14} /> Chỉ quản trị viên được thay đổi mục này.</p>;
  const submit = <div className="settings-submit"><button type="button" className="btn-text" onClick={reset} disabled={update.isPending || !dirty}>Hủy bỏ</button><button className="btn-primary" disabled={update.isPending || !dirty || invalid}><Icon name="save" size={24} filled />{update.isPending ? "Đang lưu…" : "Lưu thay đổi"}</button></div>;
  return <div className="settings-page"><header className="settings-heading"><h3><Icon name="stitch_brand" color="var(--primary)" />Cài đặt</h3><div className="row-actions"><Link className="icon-button" to="/queue?status=failed" aria-label="Thông báo hệ thống"><Icon name="notifications" /></Link>{isAdmin && <Link className="icon-button" to="/users" aria-label="Quản lý người dùng"><Icon name="person" /></Link>}</div></header>
    <div className="tabs settings-tabs" role="tablist" aria-label="Cài đặt">{TABS.map(([key, label]) => <button key={key} type="button" role="tab" id={`tab-${key}`} aria-controls="settings-panel" aria-selected={key === tab} onClick={() => setParams((current) => { const next = new URLSearchParams(current); next.set("tab", key); return next; }, { replace: true })}>{label}</button>)}</div>
    <div id="settings-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
    {settings.isLoading ? <div className="settings-form"><Skeleton h={80} /><Skeleton h={80} /><Skeleton h={160} /></div> : settings.isError ? <ErrorState msg={errorMessage(settings.error)} onRetry={() => settings.refetch()} /> : <>
      {tab === "security" && <PasswordForm />}
      <form className="settings-form" onSubmit={save} noValidate>
        {tab === "general" && <section><h3>Thông tin hệ thống</h3>{adminNote}
          <div className="field"><label htmlFor="system-name">Tên hệ thống</label><input id="system-name" className="input" value={draft.system_name} maxLength={60} disabled={!isAdmin} aria-invalid={!!nameError} aria-describedby="system-name-hint" onChange={(event) => set("system_name", event.target.value)} /><p id="system-name-hint" className={nameError ? "field-error" : "micro"}>{nameError || `Hiển thị trên thanh điều hướng và tiêu đề tab trình duyệt · ${[...draft.system_name.trim()].length}/60`}</p></div>
          <div className="field"><label htmlFor="display-timezone">Múi giờ hiển thị</label><div className="input-wrap"><select id="display-timezone" className="input input--with-right-icon" value={draft.display_timezone} disabled={!isAdmin} onChange={(event) => set("display_timezone", event.target.value as Draft["display_timezone"])}>{ZONES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><span className="input-icon input-icon--right"><Icon name="expand_more" /></span></div><p className="micro">Áp dụng cho mọi thời gian hiển thị trong CMS (danh sách video, hàng đợi, người dùng…).</p></div>
          <div className="field"><label htmlFor="ui-language">Ngôn ngữ giao diện</label><div className="input-wrap"><select id="ui-language" className="input input--with-right-icon" defaultValue="vi" disabled><option value="vi">Tiếng Việt</option></select><span className="input-icon input-icon--right"><Icon name="expand_more" /></span></div></div>
        </section>}
        {tab === "ai" && <><section><h3>Tính năng AI</h3><ToggleCard icon="magic_button" title="Tự động đánh dấu (Auto-highlighting)" description="Tự động nhận diện các đoạn quan trọng bằng phân tích đa phương thức." checked={draft.auto_highlight_enabled} onChange={(value) => set("auto_highlight_enabled", value)} /><ToggleCard icon="closed_caption" title="Tạo phụ đề tự động" description="Bật tính năng tạo phụ đề tiếng Việt cho video." checked={draft.auto_subtitle_enabled} onChange={(value) => set("auto_subtitle_enabled", value)} /><div className="field"><label htmlFor="subtitle-language">Ngôn ngữ phụ đề mặc định</label><div className="input-wrap"><select id="subtitle-language" className="input input--with-right-icon" defaultValue="vi" disabled><option value="vi">Tiếng Việt</option></select><span className="input-icon input-icon--right"><Icon name="expand_more" /></span></div></div></section>
          <section><div className="threshold-heading"><h3>Ngưỡng gợi ý AI</h3><span className="threshold-value">Theo model</span></div><div className="threshold-card"><p>Ngưỡng được AI xác định cho từng kết quả và hiển thị tại màn Highlight. Không điều chỉnh tại đây; thay đổi cài đặt không tính lại các clip đã tạo.</p></div></section></>}
        {tab === "notifications" && <section><h3>Thông báo trong CMS</h3>{adminNote}<p className="settings-note">Hiển thị trên chuông ở thanh công cụ CMS. Không gửi email hoặc thông báo đẩy.</p>
          <ToggleCard icon="error" title="Job xử lý lỗi" description="Báo khi có video xử lý thất bại cần thử lại hoặc kiểm tra." checked={draft.notify_failed_jobs} disabled={!isAdmin} onChange={(value) => set("notify_failed_jobs", value)} />
          <ToggleCard icon="category" title="Video chưa gán danh mục" description="Báo khi có video đã xử lý xong nhưng chưa được xác nhận danh mục." checked={draft.notify_uncategorized_videos} disabled={!isAdmin} onChange={(value) => set("notify_uncategorized_videos", value)} />
        </section>}
        {tab === "security" && <section><h3>Phiên đăng nhập</h3>{adminNote}
          <div className="field"><label htmlFor="session-ttl">Thời hạn phiên đăng nhập (ngày)</label><input id="session-ttl" className="input" type="number" inputMode="numeric" min={1} max={30} step={1} value={Number.isNaN(draft.session_ttl_days) ? "" : draft.session_ttl_days} disabled={!isAdmin} aria-invalid={!!ttlError} aria-describedby="session-ttl-hint" onChange={(event) => set("session_ttl_days", event.target.valueAsNumber)} /><p id="session-ttl-hint" className={ttlError ? "field-error" : "micro"}>{ttlError || "Áp dụng cho lần đăng nhập mới của mọi tài khoản (CMS và ứng dụng người xem). Phiên đang mở giữ hạn cũ."}</p></div>
          <RevokeOthers />
        </section>}
        {tab !== "security" || isAdmin ? submit : null}
      </form>
      {tab === "ai" && <div className="settings-atmosphere"><h4>Tối ưu hiệu suất</h4><p>Các thiết lập của bạn sẽ được đồng bộ hóa tức thì trên tất cả các dịch vụ xử lý video.</p></div>}
    </>}
    </div>
  </div>;
}

function RevokeOthers() {
  const revoke = useRevokeOtherSessions();
  const toast = useToast();
  const run = async () => {
    if (!confirm("Đăng xuất tài khoản này trên mọi thiết bị khác? Phiên hiện tại vẫn giữ.")) return;
    try { const { revoked } = await revoke.mutateAsync(); toast.ok(revoked ? `Đã đăng xuất ${revoked} phiên khác` : "Không có phiên nào khác đang mở"); } catch (error) { toast.err(errorMessage(error)); }
  };
  return <div className="toggle-card settings-row"><div className="min-zero"><strong>Đăng xuất mọi thiết bị khác</strong><p>Thu hồi các phiên đăng nhập khác của tài khoản bạn. Thiết bị khác cần đăng nhập lại.</p></div><button type="button" className="btn-outline" onClick={run} disabled={revoke.isPending}><Icon name="logout" size={18} />{revoke.isPending ? "Đang đăng xuất…" : "Đăng xuất thiết bị khác"}</button></div>;
}

function PasswordForm() {
  const change = useChangePassword();
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirmNext, setConfirmNext] = useState("");
  const [serverError, setServerError] = useState("");
  const bytes = new TextEncoder().encode(next).length;
  const error = !next ? "" : bytes < 8 ? "Mật khẩu mới tối thiểu 8 ký tự" : bytes > 72 ? "Mật khẩu mới quá dài (tối đa 72 byte)" : next === current ? "Mật khẩu mới phải khác mật khẩu hiện tại" : confirmNext && confirmNext !== next ? "Mật khẩu nhập lại không khớp" : "";
  const ready = !!current && !!next && confirmNext === next && !error;
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    setServerError("");
    try {
      await change.mutateAsync({ current_password: current, new_password: next });
      setCurrent(""); setNext(""); setConfirmNext("");
      toast.ok("Đã đổi mật khẩu. Các thiết bị khác đã bị đăng xuất.");
    } catch (err) { setServerError(apiCode(err) === "INVALID_CURRENT_PASSWORD" ? "Mật khẩu hiện tại không đúng" : errorMessage(err)); }
  };
  return <form className="settings-form" onSubmit={submit} noValidate aria-label="Đổi mật khẩu"><section><h3>Đổi mật khẩu</h3><p className="settings-note">Áp dụng cho tài khoản đang đăng nhập. Sau khi đổi, các thiết bị khác sẽ bị đăng xuất.</p>
    <div className="field"><label htmlFor="current-password">Mật khẩu hiện tại</label><input id="current-password" className="input" type="password" autoComplete="current-password" value={current} onChange={(event) => { setCurrent(event.target.value); setServerError(""); }} /></div>
    <div className="settings-connection"><div className="field"><label htmlFor="new-password">Mật khẩu mới</label><input id="new-password" className="input" type="password" autoComplete="new-password" value={next} aria-invalid={!!error} onChange={(event) => setNext(event.target.value)} /></div>
      <div className="field"><label htmlFor="confirm-password">Nhập lại mật khẩu mới</label><input id="confirm-password" className="input" type="password" autoComplete="new-password" value={confirmNext} onChange={(event) => setConfirmNext(event.target.value)} /></div></div>
    {(error || serverError) ? <p className="field-error" role="alert">{serverError || error}</p> : <p className="micro">Tối thiểu 8 ký tự.</p>}
    <div className="settings-submit"><button className="btn-primary" disabled={!ready || change.isPending}><Icon name="lock" size={20} />{change.isPending ? "Đang đổi…" : "Đổi mật khẩu"}</button></div>
  </section></form>;
}

function ToggleCard({ icon, title, description, checked, onChange, disabled }: { icon: string; title: string; description: string; checked: boolean; onChange: (value: boolean) => void; disabled?: boolean }) {
  return <div className="toggle-card"><span className="toggle-icon"><Icon name={icon} /></span><div className="min-zero"><strong>{title}</strong><p>{description}</p></div><label className="switch"><span /><input type="checkbox" aria-label={title} checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} /></label></div>;
}
