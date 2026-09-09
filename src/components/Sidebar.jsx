import { NavLink } from 'react-router-dom';
import { ROLES, ROUTES } from '../constants';

const LINKS_BY_ROLE = {
  [ROLES.STUDENT]: [
    { to: ROUTES.STUDENT_DASHBOARD, label: 'My complaints', end: true },
    { to: ROUTES.CREATE_COMPLAINT(), label: 'New complaint' },
  ],
  [ROLES.MANAGEMENT_OFFICER]: [{ to: ROUTES.OFFICER_DASHBOARD, label: 'Assigned complaints', end: true }],
  [ROLES.ADMIN]: [
    { to: ROUTES.ADMIN_DASHBOARD, label: 'Overview', end: true },
    { to: ROUTES.ADMIN_USERS, label: 'Users' },
    { to: ROUTES.ADMIN_DEPARTMENTS, label: 'Departments' },
    { to: ROUTES.ADMIN_AUDIT_LOGS, label: 'Audit logs' },
    { to: ROUTES.ADMIN_BACKUP_RESTORE, label: 'Backup & restore' },
  ],
};

export default function Sidebar({ role }) {
  const links = LINKS_BY_ROLE[role] || [];

  return (
    <nav className="w-full shrink-0 sm:w-56">
      <ul className="flex gap-1 overflow-x-auto sm:flex-col sm:overflow-visible">
        {links.map((link) => (
          <li key={link.to}>
            <NavLink
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `block whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? 'bg-campus-600 text-white' : 'text-ink-600 hover:bg-ink-100 hover:text-ink-900'
                }`
              }
            >
              {link.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
