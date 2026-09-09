import { Routes, Route, Navigate } from 'react-router-dom';
import { ROLES, ROUTES } from './constants';
import ProtectedRoute from './components/ProtectedRoute';
import RequireDepartmentPortal from './components/RequireDepartmentPortal';
import AppLayout from './components/AppLayout';
import { useAuth } from './auth/AuthContext';

import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import StudentDashboard from './pages/StudentDashboard';
import CreateComplaint from './pages/CreateComplaint';
import ComplaintDetails from './pages/ComplaintDetails';
import SelectDepartment from './pages/SelectDepartment';
import OfficerDashboard from './pages/OfficerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminDepartments from './pages/AdminDepartments';
import AdminAuditLogs from './pages/AdminAuditLogs';
import AdminBackupRestore from './pages/AdminBackupRestore';
import Forbidden from './pages/Forbidden';
import NotFound from './pages/NotFound';

const HOME_BY_ROLE = {
  [ROLES.STUDENT]: ROUTES.STUDENT_DASHBOARD,
  [ROLES.MANAGEMENT_OFFICER]: ROUTES.OFFICER_DASHBOARD,
  [ROLES.ADMIN]: ROUTES.ADMIN_DASHBOARD,
};

function RoleHomeRedirect() {
  const { role, isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to={ROUTES.LOGIN} replace />;
  return <Navigate to={HOME_BY_ROLE[role] || ROUTES.LOGIN} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RoleHomeRedirect />} />
      <Route path={ROUTES.LOGIN} element={<Login />} />
      <Route path={ROUTES.AUTH_CALLBACK} element={<AuthCallback />} />
      <Route path={ROUTES.FORBIDDEN} element={<Forbidden />} />

      <Route
        path={ROUTES.STUDENT_DASHBOARD}
        element={
          <ProtectedRoute allowedRoles={[ROLES.STUDENT]}>
            <AppLayout>
              <StudentDashboard />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.CREATE_COMPLAINT()}
        element={
          <ProtectedRoute allowedRoles={[ROLES.STUDENT]}>
            <AppLayout>
              <CreateComplaint />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path={ROUTES.OFFICER_SELECT_DEPARTMENT}
        element={
          <ProtectedRoute allowedRoles={[ROLES.MANAGEMENT_OFFICER]}>
            <SelectDepartment />
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.OFFICER_DASHBOARD}
        element={
          <ProtectedRoute allowedRoles={[ROLES.MANAGEMENT_OFFICER]}>
            <RequireDepartmentPortal>
              <AppLayout>
                <OfficerDashboard />
              </AppLayout>
            </RequireDepartmentPortal>
          </ProtectedRoute>
        }
      />

      <Route
        path={ROUTES.ADMIN_DASHBOARD}
        element={
          <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
            <AppLayout>
              <AdminDashboard />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.ADMIN_USERS}
        element={
          <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
            <AppLayout>
              <AdminUsers />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.ADMIN_DEPARTMENTS}
        element={
          <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
            <AppLayout>
              <AdminDepartments />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.ADMIN_AUDIT_LOGS}
        element={
          <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
            <AppLayout>
              <AdminAuditLogs />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.ADMIN_BACKUP_RESTORE}
        element={
          <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
            <AppLayout>
              <AdminBackupRestore />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Complaint details is shared across all three roles; the page itself
          adapts what it renders based on the current user's role and the
          backend's resource-level authorization response. */}
      <Route
        path={ROUTES.COMPLAINT_DETAILS()}
        element={
          <ProtectedRoute allowedRoles={[ROLES.STUDENT, ROLES.MANAGEMENT_OFFICER, ROLES.ADMIN]}>
            <AppLayout>
              <ComplaintDetails />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
