import type { Metadata } from "next";
import { Providers } from "@/components/Providers";
import "./globals.css";
export const metadata: Metadata = { title: "VidsAI — Video highlight", description: "Khám phá video và highlight AI" };
export default function RootLayout({ children }: {
    children: React.ReactNode;
}) {
    return <html lang="vi"><body><Providers>{children}</Providers></body></html>;
}
