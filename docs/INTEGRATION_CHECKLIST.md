# INTEGRATION CHECKLIST

What the frontend needs from Milan's Flask backend (and, transitively,
from Devarshi's database/API contract work). Items marked **ASSUMPTION**
are not defined in the locked Final PSD and were chosen by the frontend to
make progress — they need explicit confirmation or correction.

## 1. Confirmed / locked (already assumed correct)
- Base path `/api/v1`
- Session-based auth via cookie, `credentials: 'include'`
- Response envelope `{ "data": {...}, "error": null }`
- Roles: `STUDENT`, `MANAGEMENT_OFFICER`, `ADMIN`
- Status: `SUBMITTED, AI_ANALYZED, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED, REJECTED`
- Priority: `LOW, MEDIUM, HIGH, CRITICAL`
- Field names: `complaint_id`, `student_id`, `department_id`, `category_id`, `title`, `description`, `priority`, `status`, `created_at`, `updated_at`, `closed_at`
- AI object fields: `department_confidence`, `duplicate_score`, `recommendation`, `retrieved_complaint_ids`
- Endpoints listed in Final PSD §11 (auth, complaints, admin)

## 2. ASSUMPTIONS — please confirm or correct

### Pagination
Frontend sends: `?page=<n>&page_size=<n>`
Frontend expects: `{ "data": { "items": [...], "total": <n> }, "error": null }`
**Needed**: confirm exact param names and response shape, or tell us the
real ones so `services/api.js` and `Pagination.jsx` can be updated.

### Search / filtering
Frontend sends on `GET /complaints`: `search`, `status`, `priority`, and
(new) `department_id`.
**Needed**: confirm these are the actual accepted query parameters, and
which fields `search` matches against (title only? title + description?).

### History endpoint shape
Frontend expects `GET /complaints/{id}/history` to return either
`{ items: [...] }` or a bare array of
`{ history_id, new_status, changed_at, note }` objects.
**Needed**: confirm exact shape.

### Complaint detail resolution field
Frontend expects `GET /complaints/{id}` to optionally include a
`resolution: { resolution_text }` object once resolved.
**Needed**: confirm this is included, or where resolution text should be
fetched from instead.

### Audit log fields
Frontend expects `GET /admin/audit-logs` items to have: `audit_id`,
`actor_user_id`, `action`, `entity_type`, `entity_id`, `created_at`, and
accepts an `entity_type` filter query param.
**Needed**: confirm.

### Backup/restore/rollback responses
Frontend expects `POST /admin/backups` to optionally return
`{ backup_id }`. `POST /admin/restore` and `POST /admin/rollback/{id}`
responses are otherwise not read beyond success/failure.
**Needed**: confirm minimal response shape so success messaging can be
accurate.

## 3. NEW REQUIREMENT — officer department-portal selection

The team has requested that signing in as a `MANAGEMENT_OFFICER` first
asks them to choose one of the five departments as a "portal" before
reaching their dashboard. This is implemented entirely on the frontend
(`src/pages/SelectDepartment.jsx`, `src/auth/officerPortal.js`) and is
**explicitly not a new authorization mechanism** — see
`docs/security/access_control.md` for the full security rationale.

**What this depends on from the backend:**
- A way for a non-admin authenticated user to list the five seeded
  departments (id + name). The locked contract only has
  `GET /admin/departments` (ADMIN-only). Two options, either is fine:
  1. Add `GET /departments` (any authenticated role) returning
     `{ data: { items: [{ department_id, department_name, description, is_active }] } }`, or
  2. Relax `GET /admin/departments` to allow `MANAGEMENT_OFFICER` as well
     as `ADMIN`.
- Until one of these exists, the frontend falls back to the five baseline
  names from Final PSD §8 with `department_id: null`, so the picker still
  functions but the `department_id` filter sent to `GET /complaints` is
  omitted (harmless no-op) rather than wrong.
- **No change to `/complaints` authorization is required** — the officer's
  list is still scoped server-side to their own assignments. The
  `department_id` query param is only an additional, optional narrowing
  filter on top of that, useful once real IDs are available.

## 4. Database dependency (Devarshi)

The frontend never talks to PostgreSQL directly. Its indirect dependency
is that the API contract above stays compatible with the locked schema
(Final PSD §7): specifically that `department_id`/`department_name`,
`category_id`, and the enum columns (`role_name`, `status`, `priority`)
keep matching the values in `src/constants/index.js`. If the seeded
department list ever changes, only `BASELINE_DEPARTMENT_NAMES` (a fallback
constant, not a source of truth) needs a one-line update — the real values
always come from the API at runtime.

## 5. What's already handled without a backend contract yet
Frontend gracefully degrades everywhere a documented endpoint might not
exist yet: empty/loading/error states are implemented for every list and
detail view, and the department lookup has a working fallback (§3 above),
so a partially-implemented backend does not block frontend development or
demo-ability of unaffected pages.
