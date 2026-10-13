import { create } from "zustand";
type S = {
  file: File | null;
  loaded: number;
  total: number;
  status: "idle" | "uploading" | "success" | "error";
  error?: string;
  controller: AbortController | null;
  start: (f: File) => void;
  progress: (l: number, t: number) => void;
  done: () => void;
  fail: (m: string) => void;
  cancel: () => void;
  reset: () => void;
};
export const useUploadStore = create<S>((set, get) => ({
  file: null, loaded: 0, total: 0, status: "idle", controller: null,
  start: (file) => set({ file, loaded: 0, total: file.size, status: "uploading", controller: new AbortController() }),
  progress: (loaded, total) => set({ loaded, total }),
  done: () => set({ status: "success" }),
  fail: (error) => set({ status: "error", error }),
  cancel: () => { get().controller?.abort(); set({ status: "idle" }); },
  reset: () => set({ file: null, loaded: 0, total: 0, status: "idle", error: undefined, controller: null }),
}));
