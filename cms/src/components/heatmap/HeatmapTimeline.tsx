import { useEffect, useRef } from "react";
export function scoreToColor(score: number, threshold = 75): string {
  return score > threshold ? "var(--danger)" : "var(--primary)";
}
export function xToSecond(x: number, width: number, duration: number): number {
  return Math.round((x / width) * duration);
}
export function HeatmapTimeline({ scores, duration, currentTime, onSeek, height = 80, threshold = 75 }: { scores: { second: number; score: number }[]; duration: number; currentTime: number; onSeek: (s: number) => void; height?: number; threshold?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = c.getBoundingClientRect();
    c.width = rect.width * dpr;
    c.height = height * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width, H = height;
    ctx.clearRect(0, 0, W, H);
    if (!scores.length || !duration) return;
    // area
    ctx.beginPath();
    scores.forEach((s, i) => {
      const x = (s.second / duration) * W;
      const y = H - (s.score / 100) * H;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineTo(W, H);
    ctx.lineTo(0, H);
    ctx.closePath();
    ctx.fillStyle = "rgba(59,130,246,0.25)";
    ctx.fill();
    // line
    ctx.beginPath();
    scores.forEach((s, i) => {
      const x = (s.second / duration) * W;
      const y = H - (s.score / 100) * H;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "var(--primary)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    // danger segments — use settings threshold
    scores.forEach((s) => {
      if (s.score > threshold) {
        const x = (s.second / duration) * W;
        const y = H - (s.score / 100) * H;
        ctx.fillStyle = "var(--danger)";
        ctx.fillRect(x - 1, y, 2, H - y);
      }
    });
    // marker
    const mx = (currentTime / duration) * W;
    ctx.fillStyle = "var(--text-primary)";
    ctx.fillRect(mx, 0, 2, H);
  }, [scores, duration, currentTime, height, threshold]);
  return (
    <canvas
      ref={ref}
      style={{ width: "100%", height, display: "block", cursor: "pointer", background: "var(--bg-surface-2)", borderRadius: 8 }}
      onClick={(e) => {
        const r = (e.target as HTMLCanvasElement).getBoundingClientRect();
        onSeek(xToSecond(e.clientX - r.left, r.width, duration));
      }}
    />
  );
}
