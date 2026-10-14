import { useEffect, useRef, useState } from "react";
export function scoreToColor(score: number, threshold = 75): string {
  return score > threshold ? "var(--danger)" : "var(--primary)";
}
export function xToSecond(x: number, width: number, duration: number): number {
  return width > 0 ? Math.round(Math.max(0, Math.min(1, x / width)) * duration) : 0;
}
export function HeatmapTimeline({ scores, duration, currentTime, onSeek, height = 80, threshold = 75, selection, onSelectionChange, zoom = 1 }: {
  scores: { second: number; score: number }[]; duration: number; currentTime: number; onSeek: (seconds: number) => void; height?: number; threshold?: number; selection?: { start: number; end: number }; onSelectionChange?: (range: { start: number; end: number }) => void; zoom?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const dragging = useRef<"start" | "end" | "seek" | null>(null);
  const [tooltip, setTooltip] = useState("");
  const [width, setWidth] = useState(0);
  const visibleDuration = duration / zoom;
  const start = Math.max(0, Math.min(duration - visibleDuration, currentTime - visibleDuration / 2));
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !width) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr; canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    const primary = getComputedStyle(canvas).getPropertyValue("--primary").trim();
    ctx.fillStyle = "#eaddff"; ctx.fillRect(0, 0, width, height);
    if (duration > 0 && scores.length) {
      for (const sample of scores) {
        if (sample.second + 1 < start || sample.second > start + visibleDuration) continue;
        const x = (sample.second - start) / visibleDuration * width;
        const strength = Math.max(0, Math.min(1, (sample.score - threshold) / Math.max(1, 100 - threshold)));
        ctx.fillStyle = sample.score > threshold ? `rgba(186,26,26,${.25 + strength * .65})` : `rgba(70,21,153,${sample.score / 100 * .18})`;
        ctx.fillRect(x, 0, Math.max(1, width / visibleDuration), height);
      }
    }
    if (selection && duration > 0) {
      const left = (selection.start - start) / visibleDuration * width;
      const right = (selection.end - start) / visibleDuration * width;
      ctx.fillStyle = "rgba(70,21,153,.10)"; ctx.fillRect(left, 0, right - left, height);
      ctx.fillStyle = primary; ctx.fillRect(left, 0, 2, height); ctx.fillRect(right - 2, 0, 2, height);
      ctx.fillRect(left - 4, height / 2 - 12, 10, 24); ctx.fillRect(right - 6, height / 2 - 12, 10, 24);
    }
    const marker = duration > 0 ? (currentTime - start) / visibleDuration * width : 0;
    ctx.fillStyle = primary; ctx.fillRect(marker, 0, 2, height);
  }, [scores, duration, currentTime, height, threshold, selection, zoom, start, visibleDuration, width]);
  const position = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return Math.min(duration, start + xToSecond(event.clientX - rect.left, rect.width, visibleDuration));
  };
  const move = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const time = position(event);
    if (selection && onSelectionChange && dragging.current === "start") onSelectionChange({ ...selection, start: Math.max(0, Math.min(selection.end - .1, time)) });
    else if (selection && onSelectionChange && dragging.current === "end") onSelectionChange({ ...selection, end: Math.min(duration, Math.max(selection.start + .1, time)) });
    else if (dragging.current === "seek") onSeek(time);
  };
  return <div className="heatmap-canvas"><canvas ref={ref} style={{ width: "100%", height, display: "block", touchAction: "none", cursor: "ew-resize" }} role="slider" tabIndex={0} aria-label="Timeline highlight" aria-valuemin={0} aria-valuemax={duration} aria-valuenow={currentTime}
    onPointerDown={(event) => { event.currentTarget.setPointerCapture(event.pointerId); const rect = event.currentTarget.getBoundingClientRect(); const x = event.clientX - rect.left; const left = selection ? Math.abs(x - (selection.start - start) / visibleDuration * rect.width) : Infinity; const right = selection ? Math.abs(x - (selection.end - start) / visibleDuration * rect.width) : Infinity; dragging.current = onSelectionChange && Math.min(left, right) <= 10 ? left <= right ? "start" : "end" : "seek"; move(event); }}
    onPointerMove={(event) => { const time = position(event); const nearest = scores.reduce<{ second: number; score: number } | undefined>((best, score) => !best || Math.abs(score.second - time) < Math.abs(best.second - time) ? score : best, undefined); setTooltip(`${time.toFixed(0)}s · ${nearest?.score.toFixed(0) ?? "—"} điểm`); if (event.buttons === 1) move(event); }}
    onPointerUp={() => { dragging.current = null; }}
    onPointerCancel={() => { dragging.current = null; }}
    onKeyDown={(event) => { if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); onSeek(Math.max(0, Math.min(duration, currentTime + (event.key === "ArrowRight" ? 1 : -1)))); } }}
    title={tooltip}
  /><div className="timeline-ruler">{Array.from({ length: 7 }, (_, index) => <span key={index}>{Math.floor((start + index * visibleDuration / 6) / 60).toString().padStart(2, "0")}:{Math.floor((start + index * visibleDuration / 6) % 60).toString().padStart(2, "0")}</span>)}</div></div>;
}
