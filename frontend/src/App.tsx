import type { ReactNode } from "react";
import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { LoginPage } from "@/routes/login";
import { QueuePage } from "@/routes/operator/queue";
import { LeadDetailPage } from "@/routes/operator/lead-detail";
import { ProfilePage } from "@/routes/operator/profile";
import { MyWorkPage } from "@/routes/operator/my-work";
import { AdminDashboardPage } from "@/routes/admin/dashboard";
import { OperatorsPage } from "@/routes/admin/operators";
import { NotificationsPage } from "@/routes/notifications";
import type { Role } from "@/lib/types";

function ProtectedRoute({ allow, children }: { allow: Role | Role[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  const allowed = Array.isArray(allow) ? allow.includes(user.role) : user.role === allow;
  if (!allowed) return <Navigate to={user.role === "admin" ? "/admin" : "/queue"} replace />;
  return <>{children}</>;
}

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "admin" ? "/admin" : "/queue"} replace />;
}

/** A data router, not `<BrowserRouter>`: `useBlocker` is only available here, and
 *  the lead page relies on it to stop an operator walking away from work in
 *  progress without leaving a handover comment (FR-6). */
const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/", element: <HomeRedirect /> },
  {
    // Operators only. An admin who lands here is redirected to their own
    // dashboard -- /admin/leads is the observation view of the same data.
    path: "/queue",
    element: (
      <ProtectedRoute allow="operator">
        <QueuePage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/lead/:companyId",
    element: (
      <ProtectedRoute allow={["operator", "admin"]}>
        <LeadDetailPage />
      </ProtectedRoute>
    ),
  },
  // v1 deep links (notifications, bookmarks) still land somewhere useful.
  { path: "/review/:companyId", element: <LegacyReviewRedirect /> },
  {
    path: "/my-work",
    element: (
      <ProtectedRoute allow="operator">
        <MyWorkPage />
      </ProtectedRoute>
    ),
  },
  {
    // Both roles: the bell is a peek, this is the history.
    path: "/notifications",
    element: (
      <ProtectedRoute allow={["operator", "admin"]}>
        <NotificationsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/profile",
    element: (
      <ProtectedRoute allow={["operator", "admin"]}>
        <ProfilePage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/admin",
    element: (
      <ProtectedRoute allow="admin">
        <AdminDashboardPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/admin/operators",
    element: (
      <ProtectedRoute allow="admin">
        <OperatorsPage />
      </ProtectedRoute>
    ),
  },
  {
    // The admin "all leads" surface is the same queue with the admin tab set
    // (Jarayonda + Barchasi) and an owner column -- a second screen would be the
    // same table with a different import.
    path: "/admin/leads",
    element: (
      <ProtectedRoute allow="admin">
        <QueuePage />
      </ProtectedRoute>
    ),
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);

function LegacyReviewRedirect() {
  const path = window.location.pathname.replace(/^\/review\//, "/lead/");
  return <Navigate to={path} replace />;
}

function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
      <Toaster />
    </AuthProvider>
  );
}

export default App;
