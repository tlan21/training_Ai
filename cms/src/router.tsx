import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import { Sidebar } from "./components/common/Sidebar";
import { TopBar } from "./components/common/TopBar";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import DashboardPage from "./pages/DashboardPage";
import QueuePage from "./pages/QueuePage";
import HighlightPage from "./pages/HighlightPage";
import SubtitlesPage from "./pages/SubtitlesPage";
import VideosPage from "./pages/VideosPage";
import ClipsPage from "./pages/ClipsPage";
import CategoriesPage from "./pages/CategoriesPage";
import UsersPage from "./pages/UsersPage";
import SettingsPage from "./pages/SettingsPage";
import Placeholder from "./pages/Placeholder";

function Guard({ allow, children }: { allow?: string[]; children: React.ReactNode }) {
  const { accessToken, user } = useAuthStore();
  if (!accessToken) return <Navigate to="/login" replace />;
  if (allow && user && !allow.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
function Shell() {
  return (
    <div style={{ display: "flex" }}>
      <Sidebar />
      <div style={{ marginLeft: 260, flex: 1, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <TopBar />
        <main style={{ padding: 24, flex: 1 }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },
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
      { path: "/users", element: <Guard allow={["admin"]}><UsersPage /></Guard> },
    ],
  },
]);
