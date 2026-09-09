import { Navigate } from 'react-router-dom';
import { getSelectedDepartmentPortal } from '../auth/officerPortal';
import { ROUTES } from '../constants';

// UI-flow guard only (see src/auth/officerPortal.js for why this is not a
// security boundary). Wrap officer-only pages that assume a portal has
// already been chosen this session.
export default function RequireDepartmentPortal({ children }) {
  const selected = getSelectedDepartmentPortal();
  if (!selected) {
    return <Navigate to={ROUTES.OFFICER_SELECT_DEPARTMENT} replace />;
  }
  return children;
}
