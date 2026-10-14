import { create } from "zustand";
type T = { id: number; msg: string; kind: "ok" | "err" };
type S = { items: T[]; push: (msg: string, kind: T["kind"]) => void; remove: (id: number) => void };
const useToastStore = create<S>((set) => ({
  items: [],
  push: (msg, kind) => {
    const id = Date.now() + Math.random();
    set((s) => ({ items: [...s.items, { id, msg, kind }] }));
    setTimeout(() => useToastStore.getState().remove(id), 4500);
  },
  remove: (id) => set((s) => ({ items: s.items.filter((x) => x.id !== id) })),
}));
export function useToast() {
  const push = useToastStore((s) => s.push);
  return { ok: (m: string) => push(m, "ok"), err: (m: string) => push(m, "err") };
}
export function ToastHost() {
  const items = useToastStore((s) => s.items);
  return (
    <div style={{ position: "fixed", right: 16, top: 64, display: "grid", gap: 8, zIndex: 100, maxWidth: "min(360px, calc(100vw - 32px))", pointerEvents: "none" }}>
      {items.map((t) => (
        <div key={t.id} role={t.kind === "err" ? "alert" : "status"} style={{ padding: "10px 14px", borderRadius: 8, background: t.kind === "ok" ? "var(--success)" : "var(--danger)", color: "white", fontSize: 13, overflowWrap: "anywhere", boxShadow: "0 4px 12px rgba(29,26,34,.1)" }}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}
