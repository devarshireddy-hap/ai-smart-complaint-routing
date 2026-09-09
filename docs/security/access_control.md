# Security Decisions — Access Control

Source: Final PSD §4, §14, §33 (resource-level access); this document also
covers the officer department-portal addition and clarifies its security
posture explicitly.

## Resource-level access control
RBAC alone doesn't stop Student A from reading Student B's complaint by
editing a URL from `/complaints/101` to `/complaints/102`. The frontend
does not attempt to prevent this by hiding links only — every complaint
detail load calls `GET /complaints/{id}`, and the backend is expected to
return 403/404 for a non-owned, non-assigned, non-admin request. The
frontend's only job is to handle that response gracefully
(`ComplaintDetails.jsx` shows "This complaint isn't available" rather than
a broken page or, worse, silently rendering partial data).

## Officer department-portal selection — security clarification
A `MANAGEMENT_OFFICER` is now asked to pick one of the five seeded
departments as a "portal" right after signing in
(`src/pages/SelectDepartment.jsx`). This is explicitly **not** part of the
locked Final PSD and **must not be read as a new authorization
mechanism**:

- The selection is stored in `sessionStorage` on the client only
  (`src/auth/officerPortal.js`) and is never sent to the backend as a
  claim of identity or permission.
- It is used only to (a) choose which department's complaints to *show
  first* and (b) label the dashboard ("Electrical Department Portal").
- The complaint list the officer actually sees is still whatever
  `GET /complaints` returns for their authenticated session — i.e., only
  complaints assigned to them, per the backend's existing rule (Final PSD
  §4: "Read complaints assigned to self"). Picking "Finance" does not let
  an officer see Finance complaints they were not assigned.
- Nothing about role or resource-level enforcement changes: an officer
  assigned to a Plumbing complaint can still open it directly by ID
  regardless of which portal they picked.

**Action required from Milan/Devarshi**: there is currently no non-admin
endpoint to list departments (the locked contract only has
`GET /admin/departments`, ADMIN-only). The frontend calls a not-yet-existing
`GET /departments` and falls back to the five baseline names with no
`department_id` if that call fails, so the picker still works but
department-based filtering is inert until this is resolved. See
`INTEGRATION_CHECKLIST.md`.

## Least privilege
Officers and students only ever see UI entry points for what their role
can do; the same principle governs which backend scopes are requested and
which fields the UI even offers to edit.
