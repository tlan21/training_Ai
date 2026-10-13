import { create } from "zustand";
type S = {
  currentTime: number;
  editing: { start: number; end: number; title: string };
  setCurrentTime: (t: number) => void;
  loadClip: (p: { start: number; end: number; title?: string }) => void;
  setStart: (s: number) => void;
  setEnd: (e: number) => void;
  setTitle: (t: string) => void;
};
export const useReviewStore = create<S>((set) => ({
  currentTime: 0,
  editing: { start: 0, end: 10, title: "" },
  setCurrentTime: (currentTime) => set({ currentTime }),
  loadClip: ({ start, end, title }) => set({ editing: { start, end, title: title ?? "" } }),
  setStart: (start) => set((s) => ({ editing: { ...s.editing, start } })),
  setEnd: (end) => set((s) => ({ editing: { ...s.editing, end } })),
  setTitle: (title) => set((s) => ({ editing: { ...s.editing, title } })),
}));
