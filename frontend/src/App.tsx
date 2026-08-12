import type { ReactNode } from "react";
import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { LoginPage } from "@/routes/login";
import { QueuePage } from "@/routes/operator/queue";
import { CompanyReviewPage } from "@/routes/operator/company-review";
import { ProfilePage } from "@/routes/operator/profile";
import { MyRequestsPage } from "@/routes/operator/my-requests";
import { AdminDashboardPage } from "@/routes/admin/dashboard";
import { OperatorsPage } from "@/routes/admin/operators";
import { PermissionRequestsPage } from "@/routes/admin/permission-requests";
import { ClaimRequestsPage } from "@/routes/admin/claim-requests";
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

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<HomeRedirect />} />

      <Route
        path="/queue"
        element={
          <ProtectedRoute allow="operator">
            <QueuePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/review/:companyId"
        element={
          <ProtectedRoute allow="operator">
            <CompanyReviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute allow={["operator", "admin"]}>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/my-requests"
        element={
          <ProtectedRoute allow="operator">
            <MyRequestsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin"
        element={
          <ProtectedRoute allow="admin">
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/operators"
        element={
          <ProtectedRoute allow="admin">
            <OperatorsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/permission-requests"
        element={
          <ProtectedRoute allow="admin">
            <PermissionRequestsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/claim-requests"
        element={
          <ProtectedRoute allow="admin">
            <ClaimRequestsPage />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
      <Toaster />
    </AuthProvider>
  );
}

export default App;
