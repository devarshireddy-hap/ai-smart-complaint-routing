import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { authApi, MOCK_MODE } from '../services/api';
import { mockSignInAs } from '../mocks/mockApi';
import { MOCK_USERS } from '../mocks/mockData';
import { ROLES, ROUTES } from '../constants';

const HOME_BY_ROLE = {
  [ROLES.STUDENT]: ROUTES.STUDENT_DASHBOARD,
  [ROLES.MANAGEMENT_OFFICER]: ROUTES.OFFICER_DASHBOARD,
  [ROLES.ADMIN]: ROUTES.ADMIN_DASHBOARD,
};

export default function Login() {
  const { isAuthenticated, role, status, refresh } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  if (status !== 'loading' && isAuthenticated) {
    const from = location.state?.from?.pathname;
    return <Navigate to={from || HOME_BY_ROLE[role] || ROUTES.STUDENT_DASHBOARD} replace />;
  }

  const handleGoogleLogin = () => {
    // Full page navigation -- this must NOT be an API fetch call, since the
    // backend redirects the browser through Google's OAuth consent screen
    // (Final PSD Section 13).
    window.location.href = authApi.googleStartUrl();
  };

  const handlePracticeLogin = async (userId) => {
    mockSignInAs(userId);
    await refresh();
    navigate(HOME_BY_ROLE[MOCK_USERS[userId].role_name] || ROUTES.STUDENT_DASHBOARD, { replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-md bg-campus-600 font-mono text-lg font-semibold text-white">
            CD
          </span>
          <h1 className="mt-4 text-lg font-semibold text-ink-900">Campus Complaint Desk</h1>
          <p className="mt-1 text-sm text-ink-500">Sign in with your college Google account to continue.</p>
        </div>

        {MOCK_MODE ? (
          <div className="panel space-y-3 p-6">
            <div className="rounded-md bg-amber-50 px-3 py-2 text-center text-xs font-medium text-amber-800">
              Practice Mode is ON — no real backend needed. Pick who you want to sign in as:
            </div>
            <button type="button" className="btn-primary w-full" onClick={() => handlePracticeLogin('user-student-1')}>
              Sign in as Student (Asha Rao)
            </button>
            <button type="button" className="btn-secondary w-full" onClick={() => handlePracticeLogin('user-officer-1')}>
              Sign in as Management Officer (Vikram Nair)
            </button>
            <button type="button" className="btn-secondary w-full" onClick={() => handlePracticeLogin('user-admin-1')}>
              Sign in as Admin (Priya Menon)
            </button>
          </div>
        ) : (
          <div className="panel p-6">
            <button type="button" onClick={handleGoogleLogin} className="btn-primary w-full">
              Continue with Google
            </button>
            <p className="mt-4 text-center text-xs text-ink-400">
              Your identity is verified by Google. Access permissions are assigned by your college administrator.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
