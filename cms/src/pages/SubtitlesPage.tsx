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
import { fmtSec } from "../lib/time";

export default function SubtitlesPage() {
  const [params] = useSearchParams();
  const videoId = params.get("video_id") ?? "";
  const video = useCmsVideo(videoId);
  const subs = useSubtitles(videoId);
  const analysis = useCmsAnalysis(videoId);
  const settings = useSettings();
  const categories = useCategories();
  const qc = useQueryClient();
  const toast = useToast();
  const [segments, setSegments] = useState<components["schemas"]["SubtitleSegment"][]>([]);
  const [subsDirty, setSubsDirty] = useState(false);
  const [summary, setSummary] = useState("");
  const [category, setCategory] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
 const [priority,setPriority]=useState<NonNullable<components["schemas"]["Video"]["editorial_priority"]>>("normal");
  const [hashtagText, setHashtagText] = useState("");
  const [currentTime, setCurrentTime] = useState(0);
  const [autoScroll, setAutoScroll] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const player = useRef<PlayerHandle>(null);
  const rows = useRef<Record<number, HTMLDivElement | null>>({});
  const summaryDirty = summary !== (analysis.data?.summary ?? "");
  const categoryDirty = category !== (video.data?.category?.id ?? "");
  const hashtags = hashtagText.split(",").map(tag => tag.trim().replace(/^#/, "")).filter(Boolean);
  const metadataDirty = priority !== (video.data?.editorial_priority ?? "normal") || title !== (video.data?.title ?? "") || description !== (video.data?.description ?? "") || JSON.stringify(hashtags) !== JSON.stringify(video.data?.hashtags ?? []);
  const dirty = subsDirty || summaryDirty || categoryDirty || metadataDirty;
  const blocker = useBlocker(dirty);
  useEffect(() => { if (blocker.state === "blocked") { if (confirm("Bạn có thay đổi chưa lưu. Rời màn biên tập?")) blocker.proceed(); else blocker.reset(); } }, [blocker]);
  useEffect(() => { setSegments(subs.data?.segments ?? []); setSubsDirty(false); }, [subs.data, videoId]);
  useEffect(() => { setSummary(analysis.data?.summary ?? ""); }, [analysis.data, videoId]);
  useEffect(() => { setCategory(video.data?.category?.id ?? ""); }, [video.data, videoId]);
  useEffect(() => { setPriority(video.data?.editorial_priority ?? "normal"); setTitle(video.data?.title ?? ""); setDescription(video.data?.description ?? ""); setHashtagText((video.data?.hashtags ?? []).join(", ")); }, [video.data, videoId]);
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
      if (subsDirty) {await apiClient.put(`/api/cms/videos/${videoId}/subtitles`,{segments});setSubsDirty(false);await qc.invalidateQueries({queryKey:["subtitles",videoId]});}
      if (metadataDirty || !approve) {
        const body: components["schemas"]["VideoMetadataUpdate"] = { title, description, hashtags, editorial_priority:priority };
        await apiClient.put(`/api/cms/videos/${videoId}`, body);
      }
      if (categoryDirty && category) await apiClient.put(`/api/cms/videos/${videoId}/category`, { category_id: category });
      if (analysis.data && summaryDirty) await apiClient.put(`/api/cms/videos/${videoId}/summary`, { summary });
      if (approve) await apiClient.post(`/api/cms/videos/${videoId}/summary/approve`);
      await Promise.all([qc.invalidateQueries({ queryKey: ["analysis", videoId] }), qc.invalidateQueries({ queryKey: ["video", videoId] }), qc.invalidateQueries({ queryKey: ["videos"] })]);
      toast.ok(approve ? "Đã phê duyệt nội dung" : "Đã lưu bản nháp");
    } catch (error) { toast.err(errorMessage(error)); } finally { setSaving(false); }
  };
  const regenerate = async () => {
    if ((summaryDirty || title !== (video.data?.title ?? "")) && !confirm("Tạo lại tóm tắt và tiêu đề sẽ thay thế nội dung chưa lưu. Tiếp tục?")) return;
    setRegenerating(true);
    try { const result = await apiClient.post<paths["/api/cms/videos/{id}/summary/regenerate"]["post"]["responses"][200]["content"]["application/json"]>(`/api/cms/videos/${videoId}/summary/regenerate`); setSummary(result.data.summary ?? ""); if (result.data.suggested_title?.trim()) setTitle(result.data.suggested_title); await qc.invalidateQueries({ queryKey: ["analysis", videoId] }); toast.ok("Đã tạo lại bản nháp AI"); } catch (error) { toast.err(errorMessage(error)); } finally { setRegenerating(false); }
  };
  const exportSubtitles = () => {
    const timestamp = (seconds: number) => new Date(Math.max(0, seconds) * 1000).toISOString().slice(11, 23).replace(".", ",");
    const text = segments.map((segment, index) => `${index + 1}\n${timestamp(segment.start_time ?? 0)} --> ${timestamp(segment.end_time ?? 0)}\n${segment.text ?? ""}\n`).join("\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" })); const link = document.createElement("a"); link.href = url; link.download = `${videoId}-ban-nhap-ai.srt`; link.click(); URL.revokeObjectURL(url);
  };
  const approved = analysis.data?.summary_status === "approved" && !summaryDirty;
  return <div className="subtitle-workspace">
    <section className="subtitle-video">{!videoId && <VideoPicker />}<VideoPlayer variant="subtitle" ref={player} src={video.data?.playback_url} poster={video.data?.thumbnail_url} onTimeUpdate={setCurrentTime} /><div className="stream-heading"><h4><Icon name="movie" size={14} color="var(--primary)" />Thông tin luồng</h4><span className="stream-time">{fmtSec(currentTime)} / {fmtSec(video.data?.duration_seconds ?? 0)}</span></div><div className="stream-stats"><div><span className="field-label">Độ phân giải</span><p>{video.data?.width && video.data?.height ? `${video.data.width} × ${video.data.height}` : "—"}</p></div><div><span className="field-label">FPS</span><p>{video.data?.fps?.toFixed(2) ?? "—"}</p></div></div>{videoId && video.isError && <ErrorState msg={errorMessage(video.error)} onRetry={() => video.refetch()} />}<p className="micro">{video.data?.title ?? "Chọn video đã xử lý để biên tập phụ đề và tóm tắt."}</p></section>
    <section className="transcript-panel"><div className="panel-heading"><h4>Phụ đề AI (Vietnamese)</h4><div className="row-actions"><button className="icon-button" aria-label="Tải lại phụ đề" disabled={subsDirty || !videoId} onClick={() => subs.refetch()}><Icon name="sync" size={14} /></button><button className="icon-button" aria-label="Tải phụ đề SRT" disabled={!segments.length} onClick={exportSubtitles}><Icon name="download" size={18} /></button></div></div><p className="transcript-draft-note"><strong>BẢN NHÁP MÁY</strong> · Phụ đề AI có thể sai. Kiểm tra và sửa trước khi sử dụng.</p><div className="transcript-list">
      {videoId && subs.isLoading ? <Skeleton h={140} /> : subs.isError ? <ErrorState msg={errorMessage(subs.error)} onRetry={() => subs.refetch()} /> : !segments.length && <Empty msg={videoId ? "Chưa có phụ đề" : "Chọn video để xem phụ đề"} />}
      {segments.map((segment, index) => {
        const confidence = Math.round((segment.confidence ?? 0) * 100);
        const warning = !!segment.warning || confidence < (settings.data?.asr_warning_threshold ?? 65);
        return <div key={segment.segment_index ?? index} ref={(element) => { rows.current[index] = element; }} className={`transcript-row ${warning ? "has-warning" : ""} ${index === active ? "is-active" : ""}`}><div className="transcript-meta"><button className="timecode-button mono" onClick={() => seek(segment.start_time ?? 0)}>{fmtSec(segment.start_time ?? 0)} - {fmtSec(segment.end_time ?? 0)}</button><span className={`badge ${warning ? "confidence-low" : "confidence-badge"}`}>{warning && <Icon name="warning" size={14} />}{confidence}% tin cậy</span></div><textarea aria-label={`Nội dung phụ đề ${index + 1}`} value={segment.text ?? ""} rows={Math.max(2, Math.ceil((segment.text?.length ?? 0) / 42))} onChange={(event) => { setSegments((values) => values.map((value, position) => position === index ? { ...value, text: event.target.value } : value)); setSubsDirty(true); }} />{warning && <p className="warning-copy">{segment.warning === "blacklist" ? "Phát hiện từ cần kiểm tra." : "Phát hiện từ nhạy cảm hoặc nhiễu âm."}</p>}</div>;
      })}
    </div><div className="transcript-footer"><div className="autoscroll-row"><span className="field-label">Tự động cuộn theo video</span><label className="switch"><span /><input type="checkbox" aria-label="Tự động cuộn theo video" checked={autoScroll} onChange={(event) => setAutoScroll(event.target.checked)} /></label></div><button className="btn-secondary" disabled={!subsDirty || saving} onClick={saveSubtitles}><Icon name="save" size={18} />{saving ? "Đang lưu…" : "Lưu thay đổi phụ đề"}</button></div></section>
    <section className="summary-panel"><div className="summary-fields"><div className="summary-heading"><h3>Biên tập Tóm tắt</h3>{approved ? <span className="badge ai-badge">ĐÃ DUYỆT</span> : <span className="draft-badge"><span className="draft-dot" />BẢN NHÁP AI</span>}</div>
      {videoId && analysis.isLoading && <Skeleton h={64} />}{analysis.isError && <ErrorState msg={errorMessage(analysis.error)} onRetry={() => analysis.refetch()} />}
      <div className="field"><label htmlFor="suggested-title">Tiêu đề đề xuất</label><input id="suggested-title" className="input" value={title} onChange={event => setTitle(event.target.value)} maxLength={255} disabled={!video.data || saving || regenerating} /><button className="btn-text regenerate-button" disabled={!videoId || !analysis.data || !subs.data?.segments?.some(segment=>segment.text?.trim()) || subsDirty || regenerating || saving} onClick={regenerate}><Icon name="refresh" size={14} />{regenerating ? "Đang tạo lại…" : "Tạo lại bản nháp AI"}</button></div>
      {analysis.data?.category_match && <p className="micro">Gợi ý {analysis.data.category_match.source === "keyword" ? "từ khóa" : "AI hình ảnh"}: <button className="btn-text" disabled={saving} onClick={()=>setCategory(analysis.data!.category_match!.category_id)}>{analysis.data.category_match.name}</button> · Chọn rồi lưu để xác nhận.</p>}
      <div className="summary-two-fields"><div className="field"><label htmlFor="summary-category">Chuyên mục</label><select id="summary-category" className="input" value={category} onChange={(event) => setCategory(event.target.value)} disabled={!videoId || saving}><option value="">Chọn chuyên mục</option>{categories.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div><div className="field"><label htmlFor="video-priority">Ưu tiên biên tập</label><select id="video-priority" className="input" disabled={!video.data || saving} value={priority} onChange={event=>setPriority(event.target.value as typeof priority)} title="Nhãn biên tập, không thay đổi thứ tự xử lý AI"><option value="low">Thấp</option><option value="normal">Bình thường</option><option value="high">Cao</option></select></div></div>
      <div className="field"><label htmlFor="video-description">Mô tả chi tiết</label><textarea id="video-description" className="input" rows={4} value={description} onChange={event => setDescription(event.target.value)} maxLength={10000} disabled={!video.data || saving} /></div>
      <div className="field"><label htmlFor="ai-summary">Tóm tắt AI (TL;DR)</label><div className="summary-input"><textarea id="ai-summary" className="input" data-testid="summary-editor" value={summary} onChange={(event) => setSummary(event.target.value)} rows={6} disabled={!analysis.data || saving || regenerating} /><button className="icon-button copy-summary" aria-label="Sao chép tóm tắt" disabled={!summary} onClick={() => navigator.clipboard.writeText(summary).then(() => toast.ok("Đã sao chép"), (error: unknown) => toast.err(errorMessage(error)))}><Icon name="content_copy" size={16} /></button></div></div>
      <div className="field"><label htmlFor="editorial-hashtags">Thẻ Hashtag</label><input id="editorial-hashtags" className="input" value={hashtagText} onChange={event => setHashtagText(event.target.value)} placeholder="VD: BongDa, Highlight" disabled={!video.data || saving} /><div className="hashtag-list">{hashtags.map((tag, index) => <span className="hashtag" key={`${tag}-${index}`}>#{tag}</span>)}</div><p className="micro">Phân cách bằng dấu phẩy, tối đa 30 thẻ.</p>{analysis.data?.hashtags?.length ? <button className="btn-text" disabled={saving} onClick={() => setHashtagText(analysis.data!.hashtags!.join(", "))}>Dùng thẻ AI đề xuất</button> : null}</div>
    </div><div className="summary-footer"><button className="btn-outline" disabled={!dirty || saving} onClick={() => { if (!confirm("Hủy các thay đổi chưa lưu?")) return; setSummary(analysis.data?.summary ?? ""); setCategory(video.data?.category?.id ?? ""); setPriority(video.data?.editorial_priority ?? "normal"); setTitle(video.data?.title ?? ""); setDescription(video.data?.description ?? ""); setHashtagText((video.data?.hashtags ?? []).join(", ")); setSegments(subs.data?.segments ?? []); setSubsDirty(false); }}>Hủy thay đổi</button><button className="btn-secondary" disabled={!video.data || saving || regenerating} onClick={() => saveSummary(false)}>Lưu bản nháp</button><button className="btn-primary" disabled={!analysis.data || !summary.trim() || (approved && !categoryDirty && !metadataDirty) || saving || regenerating} onClick={() => saveSummary(true)}>Duyệt nội dung</button></div></section>
  </div>;
}
