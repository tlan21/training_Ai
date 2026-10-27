export function fmtSec(s: number, hours = false): string {
  const m = hours ? Math.floor(s / 60) % 60 : Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${hours ? `${String(Math.floor(s / 3600)).padStart(2, "0")}:` : ""}${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}
export function fmtISO(iso: string): string {
  try {
    return new Date(iso).toLocaleString("vi-VN");
  } catch {
    return iso;
  }
}
