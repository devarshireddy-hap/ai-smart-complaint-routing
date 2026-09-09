import { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { ROLES, ROUTES } from '../constants';
import LoadingState from '../components/LoadingState';

const HOME_BY_ROLE = {
  [ROLES.STUDENT]: ROUTES.STUDENT_DASHBOARD,
  [ROLES.MANAGEMENT_OFFICER]: ROUTES.OFFICER_DASHBOARD,
  [ROLES.ADMIN]: ROUTES.ADMIN_DASHBOARD,
};

// The backend's GET /auth/google/callback establishes the session and then
// redirects the browser here. This page just re-checks /me and routes by role.
export default function AuthCallback() {
  const { status, role, isAuthenticated, refresh } = useAuth();

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === 'loading') {
    return <LoadingState label="Finishing sign-in…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  return <Navigate to={HOME_BY_ROLE[role] || ROUTES.STUDENT_DASHBOARD} replace />;
}
