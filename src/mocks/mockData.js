// Fake data for PRACTICE MODE ONLY. None of this is real. It exists so the
// frontend can be clicked through and visually verified before Milan's
// Flask backend and Devarshi's database are ready. It is never used unless
// VITE_MOCK_MODE=true is set in .env (see docs/PRACTICE_MODE_GUIDE.md).

import { ROLES, STATUS, PRIORITY } from '../constants';

export const MOCK_DEPARTMENTS = [
  { department_id: 'dept-technical', department_name: 'Technical', description: 'IT and technical issues', is_active: true },
  { department_id: 'dept-finance', department_name: 'Finance', description: 'Financial and billing issues', is_active: true },
  { department_id: 'dept-electrical', department_name: 'Electrical', description: 'Electrical and power issues', is_active: true },
  { department_id: 'dept-plumbing', department_name: 'Plumbing', description: 'Water and plumbing issues', is_active: true },
  { department_id: 'dept-security', department_name: 'Security', description: 'Security and safety issues', is_active: true },
];

export const MOCK_USERS = {
  'user-student-1': { user_id: 'user-student-1', full_name: 'Asha Rao', email: 'asha.rao@college.edu', role_name: ROLES.STUDENT, is_active: true },
  'user-officer-1': { user_id: 'user-officer-1', full_name: 'Vikram Nair', email: 'vikram.nair@college.edu', role_name: ROLES.MANAGEMENT_OFFICER, is_active: true },
  'user-admin-1': { user_id: 'user-admin-1', full_name: 'Priya Menon', email: 'priya.menon@college.edu', role_name: ROLES.ADMIN, is_active: true },
  'user-student-2': { user_id: 'user-student-2', full_name: 'Rahul Verma', email: 'rahul.verma@college.edu', role_name: ROLES.STUDENT, is_active: true },
};

function isoDaysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

export const initialMockComplaints = () => [
  {
    complaint_id: 'complaint-1',
    student_id: 'user-student-1',
    title: 'Street lamp outside Block C is not working',
    description: 'The lamp near the Block C entrance has been off for about a week. It gets very dark there at night.',
    department: 'Electrical',
    department_id: 'dept-electrical',
    category_id: null,
    priority: PRIORITY.MEDIUM,
    status: STATUS.IN_PROGRESS,
    created_at: isoDaysAgo(6),
    updated_at: isoDaysAgo(1),
    closed_at: null,
    ai: {
      department_confidence: 0.93,
      duplicate_score: 0.12,
      recommendation: 'Likely a burnt-out bulb or tripped breaker. Recommend an electrician inspect the pole fixture near Block C.',
      retrieved_complaint_ids: ['complaint-4'],
    },
    resolution: null,
  },
  {
    complaint_id: 'complaint-2',
    student_id: 'user-student-1',
    title: 'Water leakage near the Block B stairwell',
    description: 'There is continuous water leakage near the Block B stairwell, it has made the floor slippery.',
    department: 'Plumbing',
    department_id: 'dept-plumbing',
    category_id: null,
    priority: PRIORITY.HIGH,
    status: STATUS.SUBMITTED,
    created_at: isoDaysAgo(1),
    updated_at: isoDaysAgo(1),
    closed_at: null,
    ai: null,
    resolution: null,
  },
  {
    complaint_id: 'complaint-3',
    student_id: 'user-student-2',
    title: 'Fee payment portal shows an incorrect balance',
    description: 'My hostel fee balance shows double the amount I actually owe after last week\u2019s payment.',
    department: 'Finance',
    department_id: 'dept-finance',
    category_id: null,
    priority: PRIORITY.CRITICAL,
    status: STATUS.RESOLVED,
    created_at: isoDaysAgo(10),
    updated_at: isoDaysAgo(2),
    closed_at: null,
    ai: {
      department_confidence: 0.88,
      duplicate_score: 0.05,
      recommendation: 'Likely a duplicate payment entry. Recommend finance office reconcile the ledger for this student ID.',
      retrieved_complaint_ids: [],
    },
    resolution: { resolution_text: 'Reconciled the ledger — a duplicate entry from the payment gateway was removed. Balance corrected.' },
  },
  {
    complaint_id: 'complaint-4',
    student_id: 'user-student-2',
    title: 'Light outside my building has been dead for several days',
    description: 'Same issue as many students have mentioned near Block C — the light pole is completely dark at night.',
    department: 'Electrical',
    department_id: 'dept-electrical',
    category_id: null,
    priority: PRIORITY.MEDIUM,
    status: STATUS.CLOSED,
    created_at: isoDaysAgo(20),
    updated_at: isoDaysAgo(14),
    closed_at: isoDaysAgo(14),
    ai: {
      department_confidence: 0.95,
      duplicate_score: 0.81,
      recommendation: 'High similarity to an existing open complaint about the same pole. Recommend merging investigation.',
      retrieved_complaint_ids: ['complaint-1'],
    },
    resolution: { resolution_text: 'Bulb replaced by facilities team.' },
  },
  {
    complaint_id: 'complaint-5',
    student_id: 'user-student-1',
    title: 'Side gate near the hostel is left unlocked at night',
    description: 'The side security gate near the hostel block has been left unlocked for the past few nights.',
    department: 'Security',
    department_id: 'dept-security',
    category_id: null,
    priority: PRIORITY.HIGH,
    status: STATUS.ASSIGNED,
    created_at: isoDaysAgo(3),
    updated_at: isoDaysAgo(2),
    closed_at: null,
    ai: {
      department_confidence: 0.9,
      duplicate_score: 0.02,
      recommendation: 'Recommend security team review the night patrol checklist for this gate.',
      retrieved_complaint_ids: [],
    },
    resolution: null,
  },
  {
    complaint_id: 'complaint-6',
    student_id: 'user-student-2',
    title: 'Lab computer in Room 214 won\u2019t boot',
    description: 'One of the lab computers has been stuck on a black screen for two weeks.',
    department: 'Technical',
    department_id: 'dept-technical',
    category_id: null,
    priority: PRIORITY.LOW,
    status: STATUS.AI_ANALYZED,
    created_at: isoDaysAgo(4),
    updated_at: isoDaysAgo(4),
    closed_at: null,
    ai: {
      department_confidence: 0.97,
      duplicate_score: 0.0,
      recommendation: 'Likely a hardware fault. Recommend IT support swap the machine or check the power supply.',
      retrieved_complaint_ids: [],
    },
    resolution: null,
  },
];

export const initialMockHistory = () => ({
  'complaint-1': [
    { history_id: 'h1', new_status: STATUS.SUBMITTED, changed_at: isoDaysAgo(6), note: 'Complaint submitted.' },
    { history_id: 'h2', new_status: STATUS.AI_ANALYZED, changed_at: isoDaysAgo(5), note: 'AI analysis completed.' },
    { history_id: 'h3', new_status: STATUS.ASSIGNED, changed_at: isoDaysAgo(4), note: 'Assigned to Vikram Nair.' },
    { history_id: 'h4', new_status: STATUS.IN_PROGRESS, changed_at: isoDaysAgo(1), note: 'Electrician dispatched.' },
  ],
  'complaint-2': [{ history_id: 'h5', new_status: STATUS.SUBMITTED, changed_at: isoDaysAgo(1), note: 'Complaint submitted.' }],
  'complaint-3': [
    { history_id: 'h6', new_status: STATUS.SUBMITTED, changed_at: isoDaysAgo(10), note: null },
    { history_id: 'h7', new_status: STATUS.ASSIGNED, changed_at: isoDaysAgo(8), note: null },
    { history_id: 'h8', new_status: STATUS.IN_PROGRESS, changed_at: isoDaysAgo(5), note: null },
    { history_id: 'h9', new_status: STATUS.RESOLVED, changed_at: isoDaysAgo(2), note: 'Ledger corrected.' },
  ],
  'complaint-4': [
    { history_id: 'h10', new_status: STATUS.SUBMITTED, changed_at: isoDaysAgo(20), note: null },
    { history_id: 'h11', new_status: STATUS.RESOLVED, changed_at: isoDaysAgo(15), note: 'Bulb replaced.' },
    { history_id: 'h12', new_status: STATUS.CLOSED, changed_at: isoDaysAgo(14), note: 'Student confirmed fix.' },
  ],
  'complaint-5': [
    { history_id: 'h13', new_status: STATUS.SUBMITTED, changed_at: isoDaysAgo(3), note: null },
    { history_id: 'h14', new_status: STATUS.ASSIGNED, changed_at: isoDaysAgo(2), note: 'Assigned to security officer.' },
  ],
  'complaint-6': [
    { history_id: 'h15', new_status: STATUS.SUBMITTED, changed_at: isoDaysAgo(4), note: null },
    { history_id: 'h16', new_status: STATUS.AI_ANALYZED, changed_at: isoDaysAgo(4), note: null },
  ],
});

export const MOCK_AUDIT_LOGS = [
  { audit_id: 'a1', actor_user_id: 'user-admin-1', action: 'ROLE_CHANGED', entity_type: 'user', entity_id: 'user-officer-1', created_at: isoDaysAgo(8) },
  { audit_id: 'a2', actor_user_id: 'user-officer-1', action: 'STATUS_CHANGED', entity_type: 'complaint', entity_id: 'complaint-1', created_at: isoDaysAgo(1) },
  { audit_id: 'a3', actor_user_id: 'user-admin-1', action: 'BACKUP_CREATED', entity_type: 'database', entity_id: null, created_at: isoDaysAgo(3) },
  { audit_id: 'a4', actor_user_id: 'user-student-1', action: 'COMPLAINT_CREATED', entity_type: 'complaint', entity_id: 'complaint-2', created_at: isoDaysAgo(1) },
];
