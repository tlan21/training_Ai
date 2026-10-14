import { forwardRef, useImperativeHandle, useRef } from "react";
import { Icon } from "../common/Icon";
export type PlayerHandle = { seekTo: (seconds: number) => void; currentTime: number };
export const VideoPlayer = forwardRef<PlayerHandle, { src?: string | null; poster?: string | null; onTimeUpdate?: (time: number) => void }>(
  ({ src, poster, onTimeUpdate }, ref) => {
    const video = useRef<HTMLVideoElement>(null);
    useImperativeHandle(ref, () => ({
      seekTo: (seconds) => { if (video.current) video.current.currentTime = seconds; onTimeUpdate?.(seconds); },
      get currentTime() { return video.current?.currentTime ?? 0; },
    }));
    return src ? <video ref={video} src={src} poster={poster ?? undefined} controls className="video-player" onTimeUpdate={(event) => onTimeUpdate?.(event.currentTarget.currentTime)} /> : <div className="video-player player-unavailable" style={poster ? { backgroundImage: `url("${poster}")` } : undefined}><span className="player-play"><Icon name="play_arrow" size={40} /></span><p>Nguồn phát video gốc chưa được cung cấp.</p></div>;
  },
);
