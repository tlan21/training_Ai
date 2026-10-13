import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "VidsAI — Video highlight", description: "Video highlight AI" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body style={{ background: "var(--bg-base)", color: "var(--text-primary)" }}>{children}</body>
    </html>
  );
}
