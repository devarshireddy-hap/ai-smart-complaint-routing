// Shared constants for the AI Smart Complaint Routing frontend.
//
// These values MUST stay in sync with the Final PSD (locked baseline) and
// the backend's enum definitions. Do not rename or add values here without
// a change-control note agreed with Devarshi (schema) and Milan (backend),
// per the project's change-control rule.

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Locked roles (Final PSD Section 4 / Section 8)
export const ROLES = {
  STUDENT: 'STUDENT',
  MANAGEMENT_OFFICER: 'MANAGEMENT_OFFICER',
  ADMIN: 'ADMIN',
};

// Locked complaint lifecycle (Final PSD Section 5 / Section 8)
export const STATUS = {
  SUBMITTED: 'SUBMITTED',
  AI_ANALYZED: 'AI_ANALYZED',
  ASSIGNED: 'ASSIGNED',
  IN_PROGRESS: 'IN_PROGRESS',
  RESOLVED: 'RESOLVED',
  CLOSED: 'CLOSED',
  REJECTED: 'REJECTED',
};

export const STATUS_ORDER = [
  STATUS.SUBMITTED,
  STATUS.AI_ANALYZED,
  STATUS.ASSIGNED,
  STATUS.IN_PROGRESS,
  STATUS.RESOLVED,
  STATUS.CLOSED,
];

export const STATUS_LABELS = {
  [STATUS.SUBMITTED]: 'Submitted',
  [STATUS.AI_ANALYZED]: 'AI analyzed',
  [STATUS.ASSIGNED]: 'Assigned',
  [STATUS.IN_PROGRESS]: 'In progress',
  [STATUS.RESOLVED]: 'Resolved',
  [STATUS.CLOSED]: 'Closed',
  [STATUS.REJECTED]: 'Rejected',
};

// Locked priority values (Final PSD Section 8) — CRITICAL, not URGENT.
export const PRIORITY = {
  LOW: 'LOW',
  MEDIUM: 'MEDIUM',
  HIGH: 'HIGH',
  CRITICAL: 'CRITICAL',
};

export const PRIORITY_LABELS = {
  [PRIORITY.LOW]: 'Low',
  [PRIORITY.MEDIUM]: 'Medium',
  [PRIORITY.HIGH]: 'High',
  [PRIORITY.CRITICAL]: 'Critical',
};

export const PRIORITY_ORDER = [PRIORITY.LOW, PRIORITY.MEDIUM, PRIORITY.HIGH, PRIORITY.CRITICAL];

// Baseline seeded departments (Final PSD Section 8). Always fetch the real
// list + IDs from the backend at runtime — this exists only as a fallback
// reference and must never be used to hardcode department IDs.
export const BASELINE_DEPARTMENT_NAMES = ['Technical', 'Finance', 'Electrical', 'Plumbing', 'Security'];

// Short descriptions shown on the officer department-portal selector.
// Display copy only — never used as a substitute for the department_id
// the backend returns.
export const BASELINE_DEPARTMENT_DESCRIPTIONS = {
  Technical: 'IT and technical issues',
  Finance: 'Financial and billing issues',
  Electrical: 'Electrical and power issues',
  Plumbing: 'Water and plumbing issues',
  Security: 'Security and safety issues',
};

// sessionStorage key for the officer's selected department portal. Session
// scoped (not persisted across browser sessions or after logout) since this
// is a display/scoping convenience layered on top of backend authorization,
// not itself a security boundary.
export const OFFICER_PORTAL_STORAGE_KEY = 'officerDepartmentPortal';

// Feedback rating bounds (Final PSD feedback schema: CHECK 1..5).
export const FEEDBACK_RATING_MIN = 1;
export const FEEDBACK_RATING_MAX = 5;

// Client-side route paths, kept in one place so pages and nav stay in sync.
export const ROUTES = {
  LOGIN: '/login',
  AUTH_CALLBACK: '/auth/callback',
  STUDENT_DASHBOARD: '/student',
  CREATE_COMPLAINT: () => '/student/complaints/new',
  COMPLAINT_DETAILS: (id = ':complaintId') => `/complaints/${id}`,
  OFFICER_SELECT_DEPARTMENT: '/officer/select-department',
  OFFICER_DASHBOARD: '/officer',
  ADMIN_DASHBOARD: '/admin',
  ADMIN_USERS: '/admin/users',
  ADMIN_DEPARTMENTS: '/admin/departments',
  ADMIN_AUDIT_LOGS: '/admin/audit-logs',
  ADMIN_BACKUP_RESTORE: '/admin/backup-restore',
  FORBIDDEN: '/forbidden',
};

export const DEFAULT_PAGE_SIZE = 10;
