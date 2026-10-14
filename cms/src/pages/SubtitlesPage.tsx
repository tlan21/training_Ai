import { useEffect, useRef, useState } from "react";
import { useSearchParams, useBlocker } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import type { components, paths } from "../api-types";
import { useSubtitles, useCmsAnalysis, useSettings, useCmsVideo, useCategories } from "../hooks/useCms";
import { apiClient, errorMessage } from "../lib/apiClient";
import { VideoPlayer, PlayerHandle } from "../components/player/VideoPlayer";
import { VideoPicker } from "../components/common/Media";
import { Icon } from "../components/common/Icon";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { useToast } from "../components/common/Toast";
import { useAuthStore } from "../stores/authStore";
import { fmtSec } from "../lib/time";

export default function SubtitlesPage() {
  const [params] = useSearchParams();
  const videoId = params.get("video_id") ?? "";
  const video = useCmsVideo(videoId);
  const subs = useSubtitles(videoId);
  const analysis = useCmsAnalysis(videoId);
  const settings = useSettings(useAuthStore((state) => state.user?.role) === "admin");
  const categories = useCategories();
  const qc = useQueryClient();
  const toast = useToast();
  const [segments, setSegments] = useState<components["schemas"]["SubtitleSegment"][]>([]);
  const [subsDirty, setSubsDirty] = useState(false);
  const [summary, setSummary] = useState("");
  const [category, setCategory] = useState("");
  const [currentTime, setCurrentTime] = useState(0);
  const [autoScroll, setAutoScroll] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const player = useRef<PlayerHandle>(null);
  const rows = useRef<Record<number, HTMLDivElement | null>>({});
  const summaryDirty = summary !== (analysis.data?.summary ?? "");
  const categoryDirty = category !== (video.data?.category?.id ?? "");
  const dirty = subsDirty || summaryDirty || categoryDirty;
  const blocker = useBlocker(dirty);
  useEffect(() => { if (blocker.state === "blocked") { if (confirm("Bạn có thay đổi chưa lưu. Rời màn biên tập?")) blocker.proceed(); else blocker.reset(); } }, [blocker]);
  useEffect(() => { setSegments(subs.data?.segments ?? []); setSubsDirty(false); }, [subs.data, videoId]);
  useEffect(() => { setSummary(analysis.data?.summary ?? ""); }, [analysis.data, videoId]);
  useEffect(() => { setCategory(video.data?.category?.id ?? ""); }, [video.data, videoId]);
  useEffect(() => { setCurrentTime(0); }, [videoId]);
  useEffect(() => { const handle = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } }; window.addEventListener("beforeunload", handle); return () => window.removeEventListener("beforeunload", handle); }, [dirty]);
  const active = segments.findIndex((segment) => currentTime >= (segment.start_time ?? 0) && currentTime < (segment.end_time ?? 0));
  useEffect(() => { if (autoScroll && active >= 0) rows.current[active]?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [active, autoScroll]);
  const seek = (time: number) => { setCurrentTime(time); player.current?.seekTo(time); };
  const saveSubtitles = async () => {
    setSaving(true);
    try { await apiClient.put(`/api/cms/videos/${videoId}/subtitles`, { segments }); setSubsDirty(false); await qc.invalidateQueries({ queryKey: ["subtitles", videoId] }); toast.ok("Đã lưu phụ đề"); } catch (error) { toast.err(errorMessage(error)); } finally { setSaving(false); }
  };
  const saveSummary = async (approve: boolean) => {
    setSaving(true);
    try {
      if (categoryDirty && category) { await apiClient.put(`/api/cms/videos/${videoId}/category`, { category_id: category }); await qc.invalidateQueries({ queryKey: ["video", videoId] }); await qc.invalidateQueries({ queryKey: ["videos"] }); }
      if (summaryDirty || !approve) await apiClient.put(`/api/cms/videos/${videoId}/summary`, { summary });
      if (approve) await apiClient.post(`/api/cms/videos/${videoId}/summary/approve`);
      await qc.invalidateQueries({ queryKey: ["analysis", videoId] });
      toast.ok(approve ? "Đã phê duyệt nội dung" : "Đã lưu bản nháp");
    } catch (error) { toast.err(errorMessage(error)); } finally { setSaving(false); }
  };
  const regenerate = async () => {
    if (summaryDirty && !confirm("Tạo lại tóm tắt sẽ thay thế nội dung chưa lưu. Tiếp tục?")) return;
    setRegenerating(true);
    try { const result = await apiClient.post<paths["/api/cms/videos/{id}/summary/regenerate"]["post"]["responses"][200]["content"]["application/json"]>(`/api/cms/videos/${videoId}/summary/regenerate`); setSummary(result.data.summary ?? ""); await qc.invalidateQueries({ queryKey: ["analysis", videoId] }); toast.ok("Đã tạo lại bản nháp AI"); } catch (error) { toast.err(errorMessage(error)); } finally { setRegenerating(false); }
  };
  const exportSubtitles = () => {
    const timestamp = (seconds: number) => new Date(Math.max(0, seconds) * 1000).toISOString().slice(11, 23).replace(".", ",");
    const text = segments.map((segment, index) => `${index + 1}\n${timestamp(segment.start_time ?? 0)} --> ${timestamp(segment.end_time ?? 0)}\n${segment.text ?? ""}\n`).join("\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" })); const link = document.createElement("a"); link.href = url; link.download = `${videoId}.srt`; link.click(); URL.revokeObjectURL(url);
  };
  const approved = analysis.data?.summary_status === "approved" && !summaryDirty;
  return <div className="subtitle-workspace">
    <section className="subtitle-video">{!videoId && <VideoPicker />}<VideoPlayer ref={player} poster={video.data?.thumbnail_url} onTimeUpdate={setCurrentTime} /><div className="stream-heading"><h4><Icon name="movie" size={18} />Thông tin luồng</h4><span className="badge ai-badge mono">{fmtSec(currentTime)} / {fmtSec(video.data?.duration_seconds ?? 0)}</span></div><div className="stream-stats"><div><span className="field-label">Độ phân giải</span><p>—</p></div><div><span className="field-label">FPS</span><p>—</p></div></div>{videoId && video.isError && <ErrorState msg={errorMessage(video.error)} onRetry={() => video.refetch()} />}<p className="micro">{video.data?.title ?? "Chọn video đã xử lý để biên tập phụ đề và tóm tắt."}</p></section>
    <section className="transcript-panel"><div className="panel-heading"><h4>Phụ đề AI (Vietnamese)</h4><div className="row-actions"><button className="icon-button" aria-label="Tải lại phụ đề" disabled={subsDirty || !videoId} onClick={() => subs.refetch()}><Icon name="refresh" size={18} /></button><button className="icon-button" aria-label="Tải phụ đề SRT" disabled={!segments.length} onClick={exportSubtitles}><Icon name="download" size={18} /></button></div></div><div className="transcript-list">
      {videoId && subs.isLoading ? <Skeleton h={140} /> : subs.isError ? <ErrorState msg={errorMessage(subs.error)} onRetry={() => subs.refetch()} /> : !segments.length && <Empty msg={videoId ? "Chưa có phụ đề" : "Chọn video để xem phụ đề"} />}
      {segments.map((segment, index) => {
        const confidence = Math.round((segment.confidence ?? 0) * 100);
        const warning = !!segment.warning || confidence < (settings.data?.asr_warning_threshold ?? 65);
        return <div key={segment.segment_index ?? index} ref={(element) => { rows.current[index] = element; }} className={`transcript-row ${warning ? "has-warning" : ""} ${index === active ? "is-active" : ""}`}><div className="transcript-meta"><button className="timecode-button mono" onClick={() => seek(segment.start_time ?? 0)}>{fmtSec(segment.start_time ?? 0)} – {fmtSec(segment.end_time ?? 0)}</button><span className={`badge ${warning ? "confidence-low" : "confidence-badge"}`}>{warning && <Icon name="warning" size={14} />}{confidence}% tin cậy</span></div><textarea aria-label={`Nội dung phụ đề ${index + 1}`} value={segment.text ?? ""} rows={Math.max(2, Math.ceil((segment.text?.length ?? 0) / 42))} onChange={(event) => { setSegments((values) => values.map((value, position) => position === index ? { ...value, text: event.target.value } : value)); setSubsDirty(true); }} />{warning && <p className="warning-copy">{segment.warning === "blacklist" ? "Phát hiện từ cần kiểm tra." : "Phát hiện từ nhạy cảm hoặc nhiễu âm."}</p>}</div>;
      })}
    </div><div className="transcript-footer"><div className="autoscroll-row"><span className="field-label">Tự động cuộn theo video</span><label className="switch"><span /><input type="checkbox" aria-label="Tự động cuộn theo video" checked={autoScroll} onChange={(event) => setAutoScroll(event.target.checked)} /></label></div><button className="btn-secondary" disabled={!subsDirty || saving} onClick={saveSubtitles}><Icon name="save" size={18} />{saving ? "Đang lưu…" : "Lưu thay đổi phụ đề"}</button></div></section>
    <section className="summary-panel"><div className="summary-fields"><div className="summary-heading"><h3>Biên tập Tóm tắt</h3><span className="badge ai-badge">{approved ? "ĐÃ DUYỆT" : "BẢN NHÁP AI"}</span></div>
      {videoId && analysis.isLoading && <Skeleton h={64} />}{analysis.isError && <ErrorState msg={errorMessage(analysis.error)} onRetry={() => analysis.refetch()} />}
      <div className="field"><label htmlFor="suggested-title">Tiêu đề đề xuất</label><input id="suggested-title" className="input" readOnly value={analysis.data?.suggested_title ?? ""} title="Tiêu đề do AI đề xuất; chưa hỗ trợ lưu tiêu đề tùy chỉnh" /><button className="btn-text regenerate-button" disabled={!videoId || !analysis.data || regenerating} onClick={regenerate}><Icon name="refresh" size={14} />{regenerating ? "Đang tạo lại…" : "Thử tiêu đề khác"}</button></div>
      <div className="summary-two-fields"><div className="field"><label htmlFor="summary-category">Chuyên mục</label><select id="summary-category" className="input" value={category} onChange={(event) => setCategory(event.target.value)} disabled={!videoId}><option value="">Chọn chuyên mục</option>{categories.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div><div className="field"><label htmlFor="video-priority">Độ ưu tiên</label><select id="video-priority" className="input" disabled defaultValue=""><option value="">Chưa hỗ trợ</option></select></div></div>
      <div className="field"><label htmlFor="video-description">Mô tả chi tiết</label><textarea id="video-description" className="input" readOnly rows={4} value={video.data?.description ?? ""} /></div>
      <div className="field"><label htmlFor="ai-summary">Tóm tắt AI (TL;DR)</label><div className="summary-input"><textarea id="ai-summary" className="input" data-testid="summary-editor" value={summary} onChange={(event) => setSummary(event.target.value)} rows={6} disabled={!analysis.data || saving || regenerating} /><button className="icon-button copy-summary" aria-label="Sao chép tóm tắt" disabled={!summary} onClick={() => navigator.clipboard.writeText(summary).then(() => toast.ok("Đã sao chép"), (error: unknown) => toast.err(errorMessage(error)))}><Icon name="content_copy" size={16} /></button></div></div>
      <div className="field"><label>Thẻ Hashtag</label><div className="hashtag-list">{analysis.data?.hashtags?.map((tag) => <span className="hashtag" key={tag}>{tag.startsWith("#") ? tag : `#${tag}`}</span>)}<button className="hashtag-add" disabled title="Chưa hỗ trợ chỉnh sửa hashtag">+ Thêm</button></div></div>
    </div><div className="summary-footer"><button className="btn-outline" disabled={!dirty || saving} onClick={() => { if (!confirm("Hủy các thay đổi chưa lưu?")) return; setSummary(analysis.data?.summary ?? ""); setCategory(video.data?.category?.id ?? ""); setSegments(subs.data?.segments ?? []); setSubsDirty(false); }}>Hủy thay đổi</button><button className="btn-secondary" disabled={!analysis.data || saving || regenerating} onClick={() => saveSummary(false)}>Lưu bản nháp</button><button className="btn-primary" disabled={!analysis.data || !summary.trim() || (approved && !categoryDirty) || saving || regenerating} onClick={() => saveSummary(true)}>Duyệt nội dung</button></div></section>
  </div>;
}
