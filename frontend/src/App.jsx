import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { Loading } from "./components/ui.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import AdminReportsPage from "./pages/AdminReportsPage.jsx";
import AdminUsersPage from "./pages/AdminUsersPage.jsx";
import AuditLogPage from "./pages/AuditLogPage.jsx";
import ClaimDetailPage from "./pages/ClaimDetailPage.jsx";
import ClaimsPage from "./pages/ClaimsPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import MemberDetailPage from "./pages/MemberDetailPage.jsx";
import MembersPage from "./pages/MembersPage.jsx";
import ProvidersPage from "./pages/ProvidersPage.jsx";

// Wraps pages that need a signed-in user (and optionally the admin role).
function RequireAuth({ adminOnly = false, children }) {
  const { user, checking, isAdmin } = useAuth();
  const location = useLocation();

  if (checking) return <Loading />;
  // Remember where the user was going so login can send them back there.
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/members" element={<MembersPage />} />
        <Route path="/members/:memberId" element={<MemberDetailPage />} />
        <Route path="/providers" element={<ProvidersPage />} />
        <Route path="/claims" element={<ClaimsPage />} />
        <Route path="/claims/:claimId" element={<ClaimDetailPage />} />
        <Route path="/admin/users" element={<RequireAuth adminOnly><AdminUsersPage /></RequireAuth>} />
        <Route path="/admin/audit-log" element={<RequireAuth adminOnly><AuditLogPage /></RequireAuth>} />
        <Route path="/admin/reports" element={<RequireAuth adminOnly><AdminReportsPage /></RequireAuth>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
