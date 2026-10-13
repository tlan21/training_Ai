"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
export default function RootPage() {
  const tok = useAuthStore((s) => s.accessToken);
  const router = useRouter();
  useEffect(() => { if (tok) router.replace("/feed"); else router.replace("/login"); }, [tok, router]);
  return <div style={{ padding: 24, textAlign: "center" }}>Đang chuyển hướng…</div>;
}
