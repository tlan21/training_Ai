import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Icon } from "../common/Icon";
export type PlayerHandle = { seekTo: (seconds: number) => void; preview: (start: number, end: number) => void; currentTime: number };
export const VideoPlayer = forwardRef<PlayerHandle, { src?: string | null; poster?: string | null; variant?: "highlight" | "subtitle"; onTimeUpdate?: (time: number) => void }>(
  ({ src, poster, variant, onTimeUpdate }, ref) => {
    const video = useRef<HTMLVideoElement>(null);
    const previewEnd = useRef<number | null>(null);
    const [playing, setPlaying] = useState(false);
    const [error, setError] = useState("");
    useEffect(() => { previewEnd.current = null; setPlaying(false); setError(""); }, [src]);
    const play = async () => {
      setError("");
      try { await video.current?.play(); } catch (cause) {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) setError("Không thể phát video. Vui lòng thử lại.");
      }
    };
    useImperativeHandle(ref, () => ({
      seekTo: (seconds) => { previewEnd.current = null; if (video.current) video.current.currentTime = seconds; onTimeUpdate?.(seconds); },
      preview: (start, end) => {
        if (!video.current || !Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) return;
        video.current.currentTime = start; previewEnd.current = end; onTimeUpdate?.(start); void play();
      },
      get currentTime() { return video.current?.currentTime ?? 0; },
    }));
    return src ? <div className={`video-frame ${variant ? `player-${variant}` : ""}`}>
      <video ref={video} src={src} poster={poster ?? undefined} controls={!variant} playsInline className="video-player" onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onError={() => setError("Không thể tải video. Vui lòng tải lại trang.")} onTimeUpdate={(event) => {
        const media = event.currentTarget;
        if (previewEnd.current !== null && media.currentTime >= previewEnd.current) {
          const end = previewEnd.current; previewEnd.current = null; media.pause(); media.currentTime = end;
        }
        onTimeUpdate?.(media.currentTime);
      }} />
      {variant && <button className="player-toggle" aria-label={playing ? "Tạm dừng video" : "Phát video"} onClick={() => { if (video.current?.paused) void play(); else video.current?.pause(); }}><Icon name={playing ? "pause" : "play_arrow"} filled size={variant === "highlight" ? 40 : 24} /></button>}
      {error && <p className="player-error" role="alert">{error}</p>}
    </div> : <div className={`video-player player-unavailable ${variant ? `player-${variant}` : ""}`} style={poster ? { backgroundImage: `url("${poster}")` } : undefined}><span className="player-play"><Icon name="play_arrow" filled size={variant === "subtitle" ? 24 : 40} /></span><p>Nguồn phát video gốc chưa được cung cấp.</p></div>;
  },
);
