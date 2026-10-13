import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import { Sidebar } from "./components/common/Sidebar";
import { TopBar } from "./components/common/TopBar";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
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
  {
    element: <Guard><Shell /></Guard>,
    children: [
      { path: "/", element: <Navigate to="/dashboard" replace /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/videos", element: <Placeholder title="Danh sách Video" /> },
      { path: "/queue", element: <Placeholder title="Hàng đợi xử lý" /> },
      { path: "/highlight", element: <Placeholder title="Highlight AI" /> },
      { path: "/categories", element: <Placeholder title="Danh mục" /> },
      { path: "/subtitles", element: <Placeholder title="Phụ đề & Tóm tắt" /> },
      { path: "/published", element: <Placeholder title="Nội dung đã xuất bản" /> },
      { path: "/settings", element: <Placeholder title="Cài đặt" /> },
      { path: "/users", element: <Guard allow={["admin"]}><Placeholder title="Người dùng" /></Guard> },
    ],
  },
]);
