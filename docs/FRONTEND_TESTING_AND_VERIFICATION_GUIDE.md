# FRONTEND TESTING AND VERIFICATION GUIDE

AI-Powered Smart Complaint Routing and Resolution System — College Edition
Owner: Gopinadh (Member 3 — Frontend + Integration)

This guide verifies that the React frontend works correctly on its own and
against Milan's Flask backend. It assumes the backend and PostgreSQL are
already running (see the backend/database READMEs for that setup).

---

## 1. Prerequisites

- Node.js 20.x and npm
- The Flask backend running locally (default assumed at `http://localhost:5000`)
- A Google OAuth test account with a user already seeded into the `users`
  table (or a backend flow that creates one on first login)

## 2. Installation

```bash
cd frontend
npm install
```

## 3. Environment setup

```bash
cp .env.example .env
```

Leave `VITE_API_BASE_URL` empty for local development — the Vite dev server
proxies `/api/v1` and `/auth` to `VITE_DEV_BACKEND_ORIGIN` (default
`http://localhost:5000`). Change `VITE_DEV_BACKEND_ORIGIN` only if the
backend runs on a different host/port.

## 4. Starting the frontend

```bash
npm run dev
```

Visit `http://localhost:5173`. You should land on `/login`.

## 5. Connecting to the Flask backend

1. Confirm the backend is running and `GET /api/v1/me` returns 401 when
   signed out (open it directly or check the Network tab).
2. Confirm `GET /auth/google/start` on the backend redirects to Google's
   consent screen. If it 404s, the backend route isn't implemented yet —
   this blocks all further testing (see INTEGRATION_CHECKLIST.md).

## 6. Login testing

| Case | Steps | Expected result |
|---|---|---|
| Successful login | Click "Continue with Google", complete consent | Redirected to `/auth/callback`, then to the role-appropriate dashboard |
| Cancelled consent | Start login, cancel on Google's screen | Returned to `/login` without a session |
| Expired session | Log in, then manually expire/delete the session cookie, reload a protected page | Redirected to `/login` |
| Direct access while logged out | Visit `/student` without logging in | Redirected to `/login`, original path preserved for post-login redirect |

## 7. Role-based routing testing

| Role | Visit | Expected |
|---|---|---|
| STUDENT | `/officer` | Redirected to `/forbidden` |
| STUDENT | `/admin` | Redirected to `/forbidden` |
| MANAGEMENT_OFFICER | `/student` | Redirected to `/forbidden` |
| ADMIN | `/student`, `/officer` | Redirected to `/forbidden` (admin has its own dashboard, not student/officer views) |

Remember: this is UI convenience only. Also verify directly against the
backend (e.g. with curl) that role/resource checks are enforced there —
the frontend redirect is not the security boundary.

## 8. Student Dashboard testing

- Log in as a STUDENT with zero complaints → empty state with "Submit your
  first complaint" call to action.
- Create a complaint, return to dashboard → it appears in the list with
  status `Submitted`.
- Use the search box → list narrows to matching titles/descriptions.
- Use the status and priority filters → list narrows accordingly.
- With more than one page of complaints → Pagination controls appear and
  paging forward/back updates the list.

## 9. Complaint creation testing

| Case | Input | Expected |
|---|---|---|
| Empty form | Submit with no title/description | Inline "Title is required." / "Description is required." errors, no request sent |
| Title too long | > 200 characters | Browser `maxLength` prevents typing further; if pasted, submit shows validation error |
| Whitespace-only | Title/description are only spaces | Treated as empty, validation error shown |
| Valid submission | Fill both fields, submit | Redirected to `/complaints/{id}`; new complaint visible with status `Submitted` |
| Backend rejects (422) | Simulate backend validation failure | Error banner shown above the form, form data preserved |

## 10. Complaint details testing

- As the owning STUDENT: title, description, priority, status, AI panel,
  similar-complaints panel, history, and (once resolved) resolution text
  all render.
- As a different STUDENT: visiting another student's complaint URL
  directly → backend returns 403/404 → page shows "This complaint isn't
  available."
- Before AI analysis has run: AI panel shows "AI analysis has not run for
  this complaint yet." instead of blank/broken UI.
- AI recommendation text renders as plain text even if it contains
  characters like `<`, `>`, or `&` — confirm no HTML is executed (paste a
  string like `<script>alert(1)</script>` into a test complaint's
  description via the backend/seed data and confirm it displays literally).

## 11. Officer Dashboard testing

- Log in as MANAGEMENT_OFFICER with complaints assigned → list shows only
  those, matching what the backend returns (do not assume the frontend
  filters — confirm via Network tab that the officer's list request
  returns the same set the UI shows).
- Open a complaint, move status forward (e.g. `Assigned → In progress`) →
  history updates, status badge changes.
- Attempt to move status to `Resolved` without entering resolution text →
  form requires it (native `required` validation).
- As ADMIN only: "Reject complaint" button is visible; as
  MANAGEMENT_OFFICER: it is not.

## 12. Admin Dashboard testing

- Overview cards show non-negative counts per status; total matches sum of
  status counts for the sampled page (see the code comment noting this is
  a client-side approximation, not a true aggregate).
- Users page: change a user's role via the dropdown → confirmation dialog
  appears → confirming calls the backend and the table refreshes.
- Departments page: list renders with active/inactive badges; there is no
  create/delete control (by design — departments are frozen).
- Audit logs page: entries paginate; filtering by entity type narrows
  results.
- Backup & Restore page: each action (backup, restore, rollback) requires
  filling required fields and passing through a confirmation dialog before
  any request is sent.

## 13. AI result / similar complaint / duplicate testing

- Complaint with a high AI department confidence → confidence bar reflects
  the percentage accurately (spot check against the raw `ai.department_confidence`
  value returned by the backend).
- Complaint flagged as a likely duplicate → duplicate-likelihood bar
  renders and similar-complaint IDs link to their own detail pages.
- Complaint with `retrieved_complaint_ids: []` → "No semantically similar
  historical complaints were retrieved." message shown, not a blank panel.

## 14. Status testing (lifecycle)

Confirm the UI only ever offers the single next forward status
(`SUBMITTED → AI_ANALYZED → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED`),
never lets a STUDENT change status, and offers `REJECTED` only to ADMIN on
non-terminal complaints. Also send a direct API request (e.g. via curl) for
an illegal transition and confirm the backend — not just the UI — rejects
it with 409/422.

## 15. Feedback testing

- Feedback form is hidden until `status` is `RESOLVED` or `CLOSED`.
- Rating outside 1–5 is rejected by the `min`/`max` input constraints.
- Successful submission shows a thank-you message and does not allow a
  second submission from the same page load (`submitted` state).

## 16. Search, filtering, and pagination testing

Run each dashboard's search/filter/pagination against a backend seeded
with more than one page of data. Confirm the URL/query parameters sent
match what's documented in `INTEGRATION_CHECKLIST.md`, since these were
frontend assumptions, not part of the locked API contract.

## 17. Validation and error handling testing

- Disconnect the backend (stop the Flask process) and repeat a data load →
  "Unable to reach the server…" error banner with a working "Try again"
  button.
- Force a 500 from the backend (or a mock) → generic "Something went wrong
  on the server." message, no raw stack trace shown to the user.
- Force a 401 mid-session (e.g. delete the session server-side) → next
  request triggers the same experience as an expired session (see §6).

## 18. Authentication testing

Covered in §6. Additionally confirm cookies are sent with
`credentials: 'include'` on every request (inspect Network tab request
headers) and that no token appears in the URL at any point.

## 19. Role-based behavior testing

Covered in §7 and §11–12. Confirm sidebar links only ever show the options
relevant to the current role (`src/components/Sidebar.jsx`).

## 20. Responsive testing

Test at minimum these breakpoints using browser dev tools device toolbar:

- 360px width (small phone) — sidebar becomes a horizontal scrollable bar,
  cards stack vertically, tables scroll horizontally without breaking
  layout.
- 768px (tablet) — two-column admin overview grid.
- 1280px+ (desktop) — full three-column complaint details layout.

## 21. API integration testing

For each page, open the Network tab and confirm:
- Request method matches `INTEGRATION_CHECKLIST.md`.
- Request body field names match the Final PSD schema field names exactly
  (snake_case: `complaint_id`, `student_id`, etc.).
- Response is unwrapped correctly from the `{ data, error }` envelope.

## 22. Automated test commands

```bash
npm run test        # run once
npm run test:watch  # watch mode
npm run lint         # ESLint
```

Current automated coverage: `StatusBadge`/`PriorityBadge` enum-correctness
tests and `CreateComplaint` form-validation/submission tests. Extend this
suite as more of the backend contract is confirmed and mockable.

## 23. Docker testing

```bash
docker build -f docker/frontend.Dockerfile -t complaint-frontend --build-arg VITE_API_BASE_URL=/api/v1 .
docker run -p 8080:80 complaint-frontend
```

Visit `http://localhost:8080`. Confirm client-side routes (e.g.
`http://localhost:8080/student`) load correctly on a hard refresh (this
verifies the nginx SPA fallback in `docker/nginx.conf`).

When running via the project's `docker-compose.yml`, confirm the frontend
container can reach the backend container using the Compose service name
(update `VITE_API_BASE_URL` accordingly for that environment).

## 24. Common integration errors and troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Login button does nothing / 404 | Backend `/auth/google/start` not implemented yet | Confirm with Milan the route exists and matches this path |
| Every page redirects to `/login` after a successful Google login | Session cookie not being set as `SameSite`-compatible, or CORS/`credentials` misconfigured | Confirm backend sets cookie with correct `SameSite`/`Secure` flags for the dev origin; confirm CORS allows credentials |
| Dashboard always empty despite data existing | Response envelope or field names differ from assumption (`items`, `total`) | Confirm actual response shape with Milan/Devarshi and update `services/api.js` accordingly |
| 403 on every officer action | Backend expects a different role string than `MANAGEMENT_OFFICER` | Confirm exact enum string in the database `roles` table matches `src/constants/index.js` |
| AI panel always shows "not run yet" | `GET /complaints/{id}` doesn't include an `ai` object, or the field name differs | Confirm exact response shape against Final PSD §12 example |

## 25. Expected results summary

A fully working integration should let a STUDENT log in, submit a
complaint, see it move through the locked lifecycle as a
MANAGEMENT_OFFICER updates it, see AI analysis and similar complaints
appear once the backend runs its pipeline, and let an ADMIN view analytics,
manage users/departments, review audit logs, and trigger (not perform
in-browser) backup/restore/rollback — all while every unauthorized
cross-role or cross-user access attempt is rejected by the backend, not
merely hidden by the UI.
