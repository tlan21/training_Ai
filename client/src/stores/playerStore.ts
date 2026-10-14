"use client";
import { create } from "zustand";
import type { components } from "../api-types";
export const HIGHLIGHT_THRESHOLD = 75;
type Range = {
    start: number;
    end: number;
};
type State = {
    currentTime: number;
    duration: number;
    isPlaying: boolean;
    autoHighlight: boolean;
    videoEl: HTMLVideoElement | null;
    offset: number;
    register: (el: HTMLVideoElement | null, offset?: number) => void;
    onTimeUpdate: (time: number) => void;
    seekTo: (time: number) => void;
    setDuration: (duration: number) => void;
    setPlaying: (playing: boolean) => void;
    togglePlay: () => void;
    setAuto: (enabled: boolean) => void;
};
export const usePlayerStore = create<State>((set, get) => ({
    currentTime: 0, duration: 0, isPlaying: false, autoHighlight: false, videoEl: null, offset: 0,
    register: (videoEl, offset = 0) => set({ videoEl, offset, autoHighlight: false, isPlaying: false, currentTime: offset }),
    onTimeUpdate: (currentTime) => set({ currentTime }),
    seekTo: (time) => { const { videoEl, offset } = get(); if (videoEl && Number.isFinite(time) && Number.isFinite(videoEl.duration))
        videoEl.currentTime = Math.max(0, Math.min(videoEl.duration, time - offset)); },
    setDuration: (duration) => set({ duration }), setPlaying: (isPlaying) => set({ isPlaying }),
    togglePlay: () => { const el = get().videoEl; if (el) {
        if (el.paused)
            void el.play().catch(() => set({ isPlaying: false }));
        else
            el.pause();
    } },
    setAuto: (autoHighlight) => set({ autoHighlight }),
}));
export function buildHighlightRanges(scores: components["schemas"]["TimelineScore"][], threshold = HIGHLIGHT_THRESHOLD): Range[] {
    const ranges: Range[] = [];
    let start: number | null = null, previous: number | null = null;
    for (const sample of scores) {
        const second = sample.second, score = sample.score;
        if (second == null || score == null || !Number.isFinite(second) || !Number.isFinite(score))
            continue;
        if (start !== null && previous !== null && second > previous + 1) {
            ranges.push({ start, end: previous + 1 });
            start = null;
        }
        if (score > threshold) {
            if (start === null)
                start = second;
        }
        else if (start !== null) {
            ranges.push({ start, end: second });
            start = null;
        }
        previous = second;
    }
    if (start !== null && previous !== null)
        ranges.push({ start, end: previous + 1 });
    return ranges;
}
export function nextHighlightStart(time: number, ranges: Range[]): number | null {
    return ranges.find(range => range.start > time)?.start ?? null;
}
