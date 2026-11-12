import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import { Sidebar } from "./components/common/Sidebar";
import { TopBar } from "./components/common/TopBar";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import QueuePage from "./pages/QueuePage";
import HighlightPage from "./pages/HighlightPage";
import SubtitlesPage from "./pages/SubtitlesPage";
import VideosPage from "./pages/VideosPage";
import ClipsPage from "./pages/ClipsPage";
import CategoriesPage from "./pages/CategoriesPage";
import UsersPage from "./pages/UsersPage";
import SettingsPage from "./pages/SettingsPage";
import { useEffect, useState } from "react";
import { useSettings } from "./hooks/useCms";
import { setDisplayTimeZone } from "./lib/time";

function Guard({ children }: { children: React.ReactNode }) {
  const { accessToken, user } = useAuthStore();
  if (!accessToken || !user || !["admin", "editor"].includes(user.role ?? "")) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
// INT-59: user management is admin-only (server also answers 403).
function AdminOnly({ children }: { children: React.ReactNode }) {
  const role = useAuthStore((state) => state.user?.role);
  return role === "admin" ? <>{children}</> : <Navigate to="/dashboard" replace />;
}
function Shell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const settings = useSettings();
  const zone = settings.data?.display_timezone;
  setDisplayTimeZone(zone); // before children render; Outlet key below re-renders pages when it changes
  useEffect(() => { document.title = settings.data?.system_name || "AI Video CMS"; }, [settings.data?.system_name]);
  return (
    <div className="cms-shell">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      {menuOpen && <button className="sidebar-backdrop" aria-label="Đóng điều hướng" onClick={() => setMenuOpen(false)} />}
      <div className="cms-workspace">
        <TopBar onMenu={() => setMenuOpen((open) => !open)} />
        <main className="cms-main">
          <Outlet key={zone ?? "browser"} />
        </main>
      </div>
    </div>
  );
}
export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/forgot-password", element: <Navigate to="/login" replace /> },
  {
    element: <Guard><Shell /></Guard>,
    children: [
      { path: "/", element: <Navigate to="/dashboard" replace /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/videos", element: <VideosPage /> },
      { path: "/queue", element: <QueuePage /> },
      { path: "/highlight", element: <HighlightPage /> },
      { path: "/categories", element: <CategoriesPage /> },
      { path: "/subtitles", element: <SubtitlesPage /> },
      { path: "/published", element: <ClipsPage /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "/users", element: <AdminOnly><UsersPage /></AdminOnly> },
    ],
  },
]);
