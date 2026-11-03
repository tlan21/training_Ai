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

export const fmtBytes = (bytes?: number | null) => bytes == null ? "—" : `${(bytes / 1024 ** 2).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} MB`;
export function fmtAgo(iso: string, now = Date.now()): string {
  const minutes = Math.max(0, Math.floor((now - new Date(iso).getTime()) / 60000));
  return minutes < 1 ? "vừa xong" : minutes < 60 ? `${minutes} phút trước` : minutes < 1440 ? `${Math.floor(minutes / 60)} giờ trước` : `${Math.floor(minutes / 1440)} ngày trước`;
}
