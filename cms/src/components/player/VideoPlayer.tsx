import { forwardRef, useImperativeHandle, useRef } from "react";
export type PlayerHandle = { seekTo: (s: number) => void; currentTime: number };
export const VideoPlayer = forwardRef<PlayerHandle, { src: string; onTimeUpdate?: (t: number) => void }>(
  ({ src, onTimeUpdate }, ref) => {
    const v = useRef<HTMLVideoElement>(null);
    useImperativeHandle(ref, () => ({
      seekTo: (s) => { if (v.current) v.current.currentTime = s; },
      get currentTime() { return v.current?.currentTime ?? 0; },
    }));
    return <video ref={v} src={src} controls style={{ width: "100%", borderRadius: 8, background: "black" }} onTimeUpdate={(e) => onTimeUpdate?.((e.target as HTMLVideoElement).currentTime)} />;
  },
);
