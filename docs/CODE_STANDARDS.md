# CODE STANDARDS

AI-Powered Smart Complaint Routing and Resolution System — College Edition
Owner: Gopinadh (Member 3) — team-wide standards, enforced primarily in the frontend

These standards are drawn from the Final PSD (§17), the Blueprint (§24), and
the Master Project Document (§37), reconciled where older documents used
different conventions.

## Python (backend, for reference — enforced by Milan/Devarshi)
- PEP 8
- `snake_case` for functions/variables/files
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Type hints where practical
- Docstrings for public/service functions
- No unused imports, no dead code, no duplicated business logic
- Routes stay thin; business logic lives in services; DB access via models/repositories; AI logic isolated from route handlers

## React (frontend — this codebase)
- **Components**: `PascalCase` filenames and component names (`ComplaintCard.jsx`)
- **Functions/variables**: `camelCase`
- **Pages** live in `src/pages/`; **reusable components** in `src/components/`
- **All API calls** go through `src/services/api.js` — no component calls `fetch()` directly
- **All shared enum values** (roles, statuses, priorities) come from `src/constants/index.js` — never inline string literals for these
- Hooks (`useState`, `useEffect`, `useCallback`) preferred over class components
- No direct database access, no SQL, no Gemini API calls, no Google OAuth client secret — ever — in frontend code
- AI-generated recommendation text is rendered only as plain JSX text nodes; `dangerouslySetInnerHTML` is never used
- One component per file; co-locate small subcomponents only when they're not reused elsewhere (e.g. `ManagementActions`/`StudentFeedbackForm` inside `ComplaintDetails.jsx`)

## Database (for reference)
- `snake_case` for tables/columns
- Plural table names (Final PSD explicitly locks this): `users`, `complaints`, `complaint_history`, `audit_logs`

## API
- Nouns for resources, HTTP methods carry the action
- JSON request/response bodies
- Stable `{ data, error }` envelope (Final PSD §12)
- Base path `/api/v1`

## Testing
- Tests validate behavior and authorization outcomes, not implementation details
- Frontend: Vitest + React Testing Library
- Every new page/component that has meaningful logic (validation, conditional rendering by role/status) gets at least one test

## Git
- Branches: `main` (stable/demo-ready), `develop` (integration), `feature/*`, `fix/*`, `docs/*`
- Commit prefixes: `feat:`, `fix:`, `db:`, `ai:`, `auth:`, `test:`, `docs:`, `chore:`
- No commits named `final`, `final2`, `latest`, `new`, `working`
- No direct feature work on `main`
- Every schema/API/security change gets a documentation update and review

## Change control
Any change to a locked value (roles, statuses, priorities, departments, API
field names) requires: old decision → new decision → reason → affected
files/endpoints → approval by all three members, per the project's
change-control rule (Final PSD §28).
