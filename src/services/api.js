// Centralized API client. Per project code standards, ALL backend calls must
// go through this file — no component should call fetch() directly.
//
// Contract assumptions (flagged for Milan/Devarshi to confirm — see
// docs/INTEGRATION_CHECKLIST.md):
//   - Session is cookie-based (secure, HttpOnly, SameSite) per Final PSD
//     Section 13. credentials: 'include' is required on every request.
//   - Every response body follows { data, error } (Final PSD Section 12).
//   - List endpoints accept `page` and `page_size` query params and return
//     { data: { items: [...], total, page, page_size }, error: null }.
//   - Filter/search params: `search`, `status`, `department_id`, `priority`.
//     These are ASSUMPTIONS — not present in the locked API contract.

import { API_BASE_URL, BASELINE_DEPARTMENT_NAMES } from '../constants';
import { mockAuthApi, mockComplaintsApi, mockDepartmentsApi, mockAdminApi } from '../mocks/mockApi';

class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, value);
    }
  });
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

function defaultErrorMessage(status) {
  switch (status) {
    case 400:
      return 'The request was invalid. Check the form and try again.';
    case 401:
      return 'Your session has expired. Please sign in again.';
    case 403:
      return "You don't have permission to do that.";
    case 404:
      return 'That item could not be found.';
    case 409:
      return 'This action conflicts with the current state of the complaint.';
    case 422:
      return 'The submitted data could not be validated.';
    case 429:
      return 'Too many requests. Please wait a moment and try again.';
    default:
      return 'Something went wrong on the server. Please try again.';
  }
}

async function request(path, { method = 'GET', body, query } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}${buildQuery(query)}`, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Unable to reach the server. Check your connection and try again.', 0, null);
  }

  let payload = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    payload = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const message = payload?.error?.message || defaultErrorMessage(response.status);
    throw new ApiError(message, response.status, payload);
  }

  return payload?.data ?? null;
}

// ---- Auth ----
const realAuthApi = {
  googleStartUrl: () => `${API_BASE_URL.replace(/\/api\/v1$/, '')}/auth/google/start`,
  logout: () => request('/auth/logout', { method: 'POST' }).catch(() => null),
  me: () => request('/me'),
};

// ---- Complaints ----
const realComplaintsApi = {
  list: (params) => request('/complaints', { query: params }),
  get: (complaintId) => request(`/complaints/${complaintId}`),
  create: (body) => request('/complaints', { method: 'POST', body }),
  update: (complaintId, body) => request(`/complaints/${complaintId}`, { method: 'PATCH', body }),
  analyze: (complaintId) => request(`/complaints/${complaintId}/analyze`, { method: 'POST' }),
  assign: (complaintId, officerId) =>
    request(`/complaints/${complaintId}/assign`, { method: 'POST', body: { officer_id: officerId } }),
  addResolution: (complaintId, resolutionText) =>
    request(`/complaints/${complaintId}/resolution`, { method: 'POST', body: { resolution_text: resolutionText } }),
  submitFeedback: (complaintId, rating, comments) =>
    request(`/complaints/${complaintId}/feedback`, { method: 'POST', body: { rating, comments } }),
  history: (complaintId) => request(`/complaints/${complaintId}/history`),
};

// ---- Departments (non-admin lookup) ----
// GAP: the locked API contract only defines `GET /admin/departments`
// (ADMIN-only). The officer department-portal selector needs a non-admin
// way to list the five seeded departments. This calls a `GET /departments`
// endpoint that does NOT yet exist in the Final PSD and MUST be confirmed
// with Milan/Devarshi (see INTEGRATION_CHECKLIST.md). Until that endpoint
// exists, this falls back to the baseline department names with a null id
// — the officer can still pick a portal for display/filtering purposes,
// but department-scoped filtering by id won't work until the real
// endpoint is in place.
const realDepartmentsApi = {
  list: async () => {
    try {
      const result = await request('/departments');
      return result?.items ?? result ?? [];
    } catch {
      return BASELINE_DEPARTMENT_NAMES.map((name) => ({ department_id: null, department_name: name }));
    }
  },
};

// ---- Admin ----
const realAdminApi = {
  listUsers: (params) => request('/admin/users', { query: params }),
  updateUserRole: (userId, roleName) =>
    request(`/admin/users/${userId}/role`, { method: 'PATCH', body: { role_name: roleName } }),
  listDepartments: () => request('/admin/departments'),
  listAuditLogs: (params) => request('/admin/audit-logs', { query: params }),
  createBackup: () => request('/admin/backups', { method: 'POST' }),
  restoreBackup: (backupId) => request('/admin/restore', { method: 'POST', body: { backup_id: backupId } }),
  rollback: (rollbackId, reason) => request(`/admin/rollback/${rollbackId}`, { method: 'POST', body: { reason } }),
};

// ---- PRACTICE MODE switch ----
// When VITE_MOCK_MODE=true, every exported API object below is swapped for
// an in-browser fake that returns realistic-looking data instead of calling
// Flask. This lets every dashboard be clicked through and visually verified
// before the real backend exists. See docs/PRACTICE_MODE_GUIDE.md.
// Nothing here changes production behavior unless that env flag is set.
const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true';

export const authApi = MOCK_MODE ? mockAuthApi : realAuthApi;
export const complaintsApi = MOCK_MODE ? mockComplaintsApi : realComplaintsApi;
export const departmentsApi = MOCK_MODE ? mockDepartmentsApi : realDepartmentsApi;
export const adminApi = MOCK_MODE ? mockAdminApi : realAdminApi;

export { ApiError, MOCK_MODE };
