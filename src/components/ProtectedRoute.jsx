import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { ROUTES } from '../constants';
import LoadingState from './LoadingState';

// Zero Trust note (Final PSD Section 22): this component only improves UX by
// avoiding a flash of the wrong page. It is NOT the authorization boundary —
// every protected backend endpoint independently re-checks identity, role,
// and resource ownership regardless of what the UI allows the user to see.
export default function ProtectedRoute({ children, allowedRoles }) {
  const { status, role, isAuthenticated } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <LoadingState label="Checking your session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to={ROUTES.FORBIDDEN} replace />;
  }

  return children;
}
