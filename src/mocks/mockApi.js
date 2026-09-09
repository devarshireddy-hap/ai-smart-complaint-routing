// PRACTICE MODE mock backend. Every function here mirrors the exact shape
// (same name, same arguments, same return shape) as the real functions in
// services/api.js, so pages never know the difference. State lives in
// sessionStorage so it survives a page refresh but resets when the tab
// closes or Practice Mode is turned off.

import {
  MOCK_DEPARTMENTS,
  MOCK_USERS,
  MOCK_AUDIT_LOGS,
  initialMockComplaints,
  initialMockHistory,
} from './mockData';
import { OFFICER_PORTAL_STORAGE_KEY } from '../constants';

const MOCK_SESSION_KEY = 'practiceMode.currentUserId';
const MOCK_COMPLAINTS_KEY = 'practiceMode.complaints';
const MOCK_HISTORY_KEY = 'practiceMode.history';

function delay(ms = 250) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function loadComplaints() {
  const raw = sessionStorage.getItem(MOCK_COMPLAINTS_KEY);
  if (raw) return JSON.parse(raw);
  const seeded = initialMockComplaints();
  sessionStorage.setItem(MOCK_COMPLAINTS_KEY, JSON.stringify(seeded));
  return seeded;
}

function saveComplaints(list) {
  sessionStorage.setItem(MOCK_COMPLAINTS_KEY, JSON.stringify(list));
}

function loadHistory() {
  const raw = sessionStorage.getItem(MOCK_HISTORY_KEY);
  if (raw) return JSON.parse(raw);
  const seeded = initialMockHistory();
  sessionStorage.setItem(MOCK_HISTORY_KEY, JSON.stringify(seeded));
  return seeded;
}

function saveHistory(map) {
  sessionStorage.setItem(MOCK_HISTORY_KEY, JSON.stringify(map));
}

function currentUser() {
  const id = sessionStorage.getItem(MOCK_SESSION_KEY);
  return id ? MOCK_USERS[id] : null;
}

// Called only by the Practice Mode login screen (see pages/Login.jsx).
export function mockSignInAs(userId) {
  sessionStorage.setItem(MOCK_SESSION_KEY, userId);
}

export function mockSignOut() {
  sessionStorage.removeItem(MOCK_SESSION_KEY);
  sessionStorage.removeItem(OFFICER_PORTAL_STORAGE_KEY);
}

export const mockAuthApi = {
  googleStartUrl: () => '#practice-mode',
  logout: async () => {
    await delay(100);
    mockSignOut();
    return null;
  },
  me: async () => {
    await delay(150);
    const user = currentUser();
    if (!user) {
      const err = new Error('Not signed in');
      err.status = 401;
      throw err;
    }
    return user;
  },
};

function paginate(items, page = 1, pageSize = 10) {
  const start = (page - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), total: items.length };
}

function matchesFilters(complaint, { search, status, priority, department_id }) {
  if (search && !`${complaint.title} ${complaint.description}`.toLowerCase().includes(search.toLowerCase())) {
    return false;
  }
  if (status && complaint.status !== status) return false;
  if (priority && complaint.priority !== priority) return false;
  if (department_id && complaint.department_id !== department_id) return false;
  return true;
}

export const mockComplaintsApi = {
  list: async (params = {}) => {
    await delay();
    const user = currentUser();
    let items = loadComplaints();

    if (user?.role_name === 'STUDENT') {
      items = items.filter((c) => c.student_id === user.user_id);
    } else if (user?.role_name === 'MANAGEMENT_OFFICER') {
      // Practice Mode: the pretend officer is "assigned" to every complaint
      // that isn't still SUBMITTED, to make the dashboard non-empty.
      items = items.filter((c) => c.status !== 'SUBMITTED');
    }

    items = items.filter((c) => matchesFilters(c, params));
    return paginate(items, Number(params.page) || 1, Number(params.page_size) || 10);
  },

  get: async (complaintId) => {
    await delay();
    const items = loadComplaints();
    const found = items.find((c) => c.complaint_id === complaintId);
    if (!found) {
      const err = new Error('Not found');
      err.status = 404;
      throw err;
    }
    return found;
  },

  create: async (body) => {
    await delay(400);
    const user = currentUser();
    const items = loadComplaints();
    const newComplaint = {
      complaint_id: `complaint-${Date.now()}`,
      student_id: user?.user_id,
      title: body.title,
      description: body.description,
      department: null,
      department_id: null,
      priority: 'MEDIUM',
      status: 'SUBMITTED',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      closed_at: null,
      ai: null,
      resolution: null,
    };
    items.unshift(newComplaint);
    saveComplaints(items);

    const historyMap = loadHistory();
    historyMap[newComplaint.complaint_id] = [
      { history_id: `h-${Date.now()}`, new_status: 'SUBMITTED', changed_at: new Date().toISOString(), note: 'Complaint submitted.' },
    ];
    saveHistory(historyMap);

    return newComplaint;
  },

  update: async (complaintId, body) => {
    await delay(300);
    const items = loadComplaints();
    const idx = items.findIndex((c) => c.complaint_id === complaintId);
    if (idx === -1) {
      const err = new Error('Not found');
      err.status = 404;
      throw err;
    }
    items[idx] = { ...items[idx], ...body, updated_at: new Date().toISOString() };
    saveComplaints(items);

    if (body.status) {
      const historyMap = loadHistory();
      const entries = historyMap[complaintId] || [];
      entries.push({
        history_id: `h-${Date.now()}`,
        new_status: body.status,
        changed_at: new Date().toISOString(),
        note: body.note || null,
      });
      historyMap[complaintId] = entries;
      saveHistory(historyMap);
    }

    return { complaint_id: complaintId, status: items[idx].status };
  },

  analyze: async (complaintId) => {
    await delay(500);
    return { complaint_id: complaintId, status: 'AI_ANALYZED' };
  },

  assign: async (complaintId) => {
    await delay(300);
    return { complaint_id: complaintId, status: 'ASSIGNED' };
  },

  addResolution: async (complaintId, resolutionText) => {
    await delay(300);
    const items = loadComplaints();
    const idx = items.findIndex((c) => c.complaint_id === complaintId);
    if (idx !== -1) {
      items[idx] = { ...items[idx], resolution: { resolution_text: resolutionText } };
      saveComplaints(items);
    }
    return { complaint_id: complaintId };
  },

  submitFeedback: async () => {
    await delay(250);
    return { submitted: true };
  },

  history: async (complaintId) => {
    await delay(200);
    const historyMap = loadHistory();
    return { items: historyMap[complaintId] || [] };
  },
};

export const mockDepartmentsApi = {
  list: async () => {
    await delay(150);
    return MOCK_DEPARTMENTS;
  },
};

export const mockAdminApi = {
  listUsers: async (params = {}) => {
    await delay();
    let items = Object.values(MOCK_USERS);
    if (params.search) {
      const q = params.search.toLowerCase();
      items = items.filter((u) => u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
    }
    return paginate(items, Number(params.page) || 1, Number(params.page_size) || 10);
  },
  updateUserRole: async (userId, roleName) => {
    await delay(300);
    if (MOCK_USERS[userId]) {
      MOCK_USERS[userId] = { ...MOCK_USERS[userId], role_name: roleName };
    }
    return { user_id: userId, role_name: roleName };
  },
  listDepartments: async () => {
    await delay(150);
    return { items: MOCK_DEPARTMENTS };
  },
  listAuditLogs: async (params = {}) => {
    await delay();
    let items = MOCK_AUDIT_LOGS;
    if (params.entity_type) {
      items = items.filter((l) => l.entity_type.toLowerCase().includes(params.entity_type.toLowerCase()));
    }
    return paginate(items, Number(params.page) || 1, Number(params.page_size) || 10);
  },
  createBackup: async () => {
    await delay(600);
    return { backup_id: `backup-${Date.now()}` };
  },
  restoreBackup: async () => {
    await delay(800);
    return { restored: true };
  },
  rollback: async () => {
    await delay(500);
    return { rolled_back: true };
  },
};
