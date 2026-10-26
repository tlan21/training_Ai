"use client";
import { useEffect } from "react";
import type { RefObject } from "react";
import { track } from "@/lib/content";
import { useAuthStore } from "@/stores/authStore";
export function useWatchTime(ref: RefObject<HTMLVideoElement>, videoId?: string, clipId?: string, active = true, source?: string | null, feed = false) {
    const userId = useAuthStore(s => s.user?.role === "client" ? s.user.id : undefined);
    useEffect(() => {
        const el = ref.current;
        if (!el || !videoId || !active || !source || !userId) return;
        let total = 0, shown = 0, previous = performance.now(), mediaTime = el.currentTime;
        let playing = !el.paused, visible = !document.hidden, sent = false;
        const sample = () => {
            const now = performance.now(), elapsed = Math.max(0, (now - previous) / 1000), delta = el.currentTime - mediaTime;
            if (visible) shown += elapsed;
            // Seeking jumps are not playback; cap repeats at one item length for the training contract.
            if (playing && visible && !el.seeking && delta > 0 && delta <= elapsed * el.playbackRate + .25)
                total = Math.min(total + delta, Number.isFinite(el.duration) ? el.duration : total + delta);
            previous = now; mediaTime = el.currentTime;
        };
        const finish = () => {
            if (sent) return;
            sample(); sent = true;
            if (useAuthStore.getState().user?.id !== userId) return;
            track({ video_id: videoId, clip_id: clipId, interaction_type: "watch_time", duration_watched: Math.floor(total) }, true);
            if (feed && shown >= 1 && total < 3) track({ video_id: videoId, clip_id: clipId, interaction_type: "skip" }, true);
        };
        const onPlay = () => { sample(); playing = true; };
        const onPause = () => { sample(); playing = false; };
        const onSeek = () => { sample(); mediaTime = el.currentTime; };
        const onVisibility = () => { sample(); visible = !document.hidden; };
        const onShow = (e: PageTransitionEvent) => { if (e.persisted) { total = 0; shown = 0; sent = false; previous = performance.now(); mediaTime = el.currentTime; visible = !document.hidden; playing = !el.paused; } };
        el.addEventListener("playing", onPlay); el.addEventListener("pause", onPause); el.addEventListener("timeupdate", sample);
        el.addEventListener("seeking", onSeek); el.addEventListener("seeked", onSeek);
        document.addEventListener("visibilitychange", onVisibility); window.addEventListener("pagehide", finish); window.addEventListener("pageshow", onShow);
        return () => {
            finish(); el.removeEventListener("playing", onPlay); el.removeEventListener("pause", onPause); el.removeEventListener("timeupdate", sample);
            el.removeEventListener("seeking", onSeek); el.removeEventListener("seeked", onSeek);
            document.removeEventListener("visibilitychange", onVisibility); window.removeEventListener("pagehide", finish); window.removeEventListener("pageshow", onShow);
        };
    }, [ref, videoId, clipId, active, source, feed, userId]);
}
