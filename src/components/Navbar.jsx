import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { getSelectedDepartmentPortal, clearSelectedDepartmentPortal } from '../auth/officerPortal';
import { ROLES, ROUTES } from '../constants';

const HOME_BY_ROLE = {
  [ROLES.STUDENT]: ROUTES.STUDENT_DASHBOARD,
  [ROLES.MANAGEMENT_OFFICER]: ROUTES.OFFICER_DASHBOARD,
  [ROLES.ADMIN]: ROUTES.ADMIN_DASHBOARD,
};

function roleLabel(role) {
  switch (role) {
    case ROLES.STUDENT:
      return 'Student';
    case ROLES.MANAGEMENT_OFFICER:
      return 'Management officer';
    case ROLES.ADMIN:
      return 'Administrator';
    default:
      return '';
  }
}

export default function Navbar() {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const portal = role === ROLES.MANAGEMENT_OFFICER ? getSelectedDepartmentPortal() : null;

  const handleLogout = async () => {
    clearSelectedDepartmentPortal();
    await logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  const switchPortal = () => {
    clearSelectedDepartmentPortal();
    navigate(ROUTES.OFFICER_SELECT_DEPARTMENT);
  };

  return (
    <header className="border-b border-ink-100 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <Link to={HOME_BY_ROLE[role] || ROUTES.LOGIN} className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-campus-600 font-mono text-sm font-semibold text-white">
            CD
          </span>
          <span className="text-sm font-semibold text-ink-900">Campus Complaint Desk</span>
        </Link>

        {user && (
          <div className="flex items-center gap-3">
            {portal?.department_name && location.pathname !== ROUTES.OFFICER_SELECT_DEPARTMENT && (
              <button
                type="button"
                onClick={switchPortal}
                className="hidden items-center gap-1 rounded-full bg-campus-50 px-3 py-1 text-xs font-medium text-campus-700 hover:bg-campus-100 sm:flex"
                title="Switch department portal"
              >
                {portal.department_name} portal
                <span aria-hidden="true">↕</span>
              </button>
            )}
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-ink-800">{user.full_name}</p>
              <p className="text-xs text-ink-500">{roleLabel(role)}</p>
            </div>
            <button type="button" onClick={handleLogout} className="btn-secondary">
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
