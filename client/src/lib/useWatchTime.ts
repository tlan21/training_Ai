"use client";
import { useEffect } from "react";
import type { RefObject } from "react";
import { apiClient } from "@/lib/apiClient";
import { track } from "@/lib/content";
import { useAuthStore } from "@/stores/authStore";
export function useWatchTime(ref: RefObject<HTMLVideoElement>, videoId?: string, clipId?: string, active = true, source?: string | null) {
    useEffect(() => {
        const el = ref.current;
        if (!el || !videoId || !active || !source)
            return;
        let total = 0, pending = 0, previous = performance.now(), playing = !el.paused;
        const sample = () => {
            const now = performance.now(), delta = Math.max(0, (now - previous) / 1000);
            previous = now;
            if (playing && !document.hidden) {
                const cap = Number.isFinite(el.duration) ? el.duration : 0;
                const addition = Math.min(delta, Math.max(0, cap - total));
                total += addition;
                pending += addition;
            }
        };
        const flush = (keepalive = false) => {
            sample();
            const watched = Math.floor(pending);
            if (watched <= 0)
                return;
            pending -= watched;
            const body = { video_id: videoId, clip_id: clipId, interaction_type: "watch_time" as const, duration_watched: watched };
            // sendBeacon cannot attach the contract's Bearer header; keepalive preserves it on page exit.
            if (keepalive)
                void fetch(`${apiClient.defaults.baseURL}/api/interactions`, { method: "POST", credentials: "include", keepalive: true, headers: { "Content-Type": "application/json", Authorization: `Bearer ${useAuthStore.getState().accessToken}` }, body: JSON.stringify(body) }).catch(() => { });
            else
                track(body);
        };
        const onPlay = () => { sample(); playing = true; };
        const onPause = () => { sample(); playing = false; };
        const onTime = () => { sample(); if (pending >= 10)
            flush(); };
        const onVisibility = () => { if (document.hidden)
            flush(true); previous = performance.now(); };
        el.addEventListener("playing", onPlay);
        el.addEventListener("pause", onPause);
        el.addEventListener("timeupdate", onTime);
        document.addEventListener("visibilitychange", onVisibility);
        return () => { flush(true); if (total < 2)
            track({ video_id: videoId, clip_id: clipId, interaction_type: "skip" }); el.removeEventListener("playing", onPlay); el.removeEventListener("pause", onPause); el.removeEventListener("timeupdate", onTime); document.removeEventListener("visibilitychange", onVisibility); };
    }, [ref, videoId, clipId, active, source]);
}
