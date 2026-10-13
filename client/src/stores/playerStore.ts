"use client";
import { create } from "zustand";
type S = {
  currentTime: number; duration: number; isPlaying: boolean; autoHighlight: boolean;
  videoEl: HTMLVideoElement | null;
  register: (el: HTMLVideoElement) => void;
  onTimeUpdate: (t: number) => void;
  seekTo: (t: number) => void;
  setDuration: (d: number) => void;
  togglePlay: () => void;
  setAuto: (v: boolean) => void;
};
export const usePlayerStore = create<S>((set, get) => ({
  currentTime: 0, duration: 0, isPlaying: false, autoHighlight: false, videoEl: null,
  register: (el) => set({ videoEl: el }),
  onTimeUpdate: (t) => {
    const { autoHighlight, videoEl } = get();
    set({ currentTime: t });
    // auto-highlight skip handled by caller passing ranges; minimal here
    if (autoHighlight && videoEl) { /* consumer will seek via ranges */ }
  },
  seekTo: (t) => { const el = get().videoEl; if (el) { el.currentTime = t; set({ currentTime: t }); } },
  setDuration: (d) => set({ duration: d }),
  togglePlay: () => {
    const el = get().videoEl; if (!el) return;
    if (el.paused) { el.play(); set({ isPlaying: true }); } else { el.pause(); set({ isPlaying: false }); }
  },
  setAuto: (v) => set({ autoHighlight: v }),
}));
export function buildHighlightRanges(scores: { second: number; score: number }[], thr = 75): { start: number; end: number }[] {
  const ranges: { start: number; end: number }[] = [];
  let s: number | null = null;
  for (let i = 0; i < scores.length; i++) {
    const sc = scores[i].score;
    if (sc > thr && s === null) s = scores[i].second;
    else if (sc <= thr && s !== null) { ranges.push({ start: s, end: scores[i].second }); s = null; }
  }
  if (s !== null) ranges.push({ start: s, end: scores[scores.length - 1].second + 1 });
  return ranges;
}
export function nextHighlightStart(t: number, ranges: { start: number; end: number }[]): number | null {
  for (const r of ranges) if (r.start > t) return r.start;
  return null;
}
