"use client";
import { useEffect, useRef, useState } from "react";
import type { components } from "@/api-types";
import { Icon } from "@/components/Icon";
import { PageState } from "@/components/Media";
import { formatTime } from "@/lib/content";
export function Transcript({ segments, loading, error, currentTime, seek, close, retry, videoId }: {
    segments: components["schemas"]["SubtitleSegment"][];
    loading: boolean;
    error: unknown;
    currentTime: number;
    seek: (time: number) => void;
    close?: () => void;
    retry: () => void;
    videoId: string;
}) {
    const [q, setQ] = useState("");
    const rows = useRef<HTMLDivElement>(null);
    const active = segments.findIndex(s => currentTime >= (s.start_time || 0) && currentTime < (s.end_time || 0));
    useEffect(() => { const container = rows.current, item = container?.querySelector<HTMLElement>('[aria-current="true"]'); if (container && item && !q) {
        const top = item.offsetTop - container.offsetTop;
        if (top < container.scrollTop || top + item.clientHeight > container.scrollTop + container.clientHeight)
            container.scrollTo({ top: Math.max(0, top - 40), behavior: "smooth" });
    } }, [active, q]);
    const download = () => { const text = segments.map(s => `[${formatTime(s.start_time)}–${formatTime(s.end_time)}] ${s.text || ""}`).join("\n"); const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" })); const a = document.createElement("a"); a.href = url; a.download = `${videoId}.txt`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
    const filtered = segments.map((s, i) => ({ s, i })).filter(({ s }) => s.text?.toLocaleLowerCase("vi").includes(q.toLocaleLowerCase("vi")));
    return <section className="transcript-panel"><header className="transcript-heading"><h2><Icon name="description"/><span className="desktop-only">Bản ghi phụ đề</span><span className="mobile-only">Bản ghi Nội dung</span></h2>{close && <button className="icon-button" onClick={close} aria-label="Đóng bản ghi"><Icon name="close"/></button>}</header>
 <div className="transcript-search"><div className="input-wrap"><span className="input-icon input-icon--left"><Icon name="search" size={18}/></span><input className="input input--with-left-icon" placeholder="Tìm trong bản ghi..." aria-label="Tìm trong bản ghi" value={q} onChange={e => setQ(e.target.value)}/></div></div>
 <div className="transcript-list" ref={rows}>{loading || error || !segments.length ? <PageState loading={loading} error={error} empty="Chưa có phụ đề." retry={retry}/> : !filtered.length ? <PageState empty="Không có câu khớp."/> : filtered.map(({ s, i }) => <button key={s.segment_index ?? i} aria-current={i === active ? "true" : undefined} className={`transcript-row ${i === active ? "active" : ""} ${s.warning ? "warning" : ""}`} onClick={() => seek(s.start_time || 0)}><time>{formatTime(s.start_time)}</time><span>{s.text}</span></button>)}</div>
 <footer className="transcript-footer"><button onClick={download} disabled={!segments.length}><Icon name="file_download" size={18}/>Tải bản ghi (.txt)</button></footer></section>;
}
