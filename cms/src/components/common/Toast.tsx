import { create } from "zustand";
type T = { id: number; msg: string; kind: "ok" | "err" };
type S = { items: T[]; push: (msg: string, kind: T["kind"]) => void; remove: (id: number) => void };
const useToastStore = create<S>((set) => ({
  items: [],
  push: (msg, kind) => set((s) => ({ items: [...s.items, { id: Date.now() + Math.random(), msg, kind }] })),
  remove: (id) => set((s) => ({ items: s.items.filter((x) => x.id !== id) })),
}));
export function useToast() {
  const push = useToastStore((s) => s.push);
  return { ok: (m: string) => push(m, "ok"), err: (m: string) => push(m, "err") };
}
export function ToastHost() {
  const items = useToastStore((s) => s.items);
  const remove = useToastStore((s) => s.remove);
  return (
    <div style={{ position: "fixed", right: 16, bottom: 16, display: "grid", gap: 8, zIndex: 100 }}>
      {items.map((t) => (
        <div key={t.id} onAnimationEnd={() => setTimeout(() => remove(t.id), 3000)} style={{ padding: "10px 14px", borderRadius: 8, background: t.kind === "ok" ? "var(--success)" : "var(--danger)", color: "white", fontSize: 13, minWidth: 260, boxShadow: "0 8px 24px rgba(0,0,0,.3)" }}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}
