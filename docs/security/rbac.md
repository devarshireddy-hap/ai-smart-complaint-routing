# Security Decisions — RBAC

Source: Final PSD §4 (locked roles/privileges table).

## Roles (exact values — `src/constants/index.js`)
`STUDENT`, `MANAGEMENT_OFFICER`, `ADMIN`

## Single users table
Per the academic requirement (DBMS PROJECT.pdf §6) and the Final PSD
schema, all users — regardless of role — live in one `users` table
distinguished by `role_id`. The frontend never assumes a separate
"student"/"officer"/"admin" account model; `GET /me` returns one user
object with a `role_name` field, and every page branches on that single
value.

## Privilege summary as reflected in the UI

**STUDENT**
- Create a complaint; view/track own complaints; submit feedback after resolution
- Cannot see other students' complaints, assign officers, or view audit logs

**MANAGEMENT_OFFICER**
- View complaints assigned to self; update permitted status fields; add a resolution
- Cannot reassign (baseline: no), manage users, or perform backup/restore/rollback
- New in this iteration: a department "portal" selector at login — display/routing convenience only, does not expand what the backend allows an officer to see (see `access_control.md`)

**ADMIN**
- Manage users/roles, departments, view all complaints, assign officers, view audit logs, initiate backup/restore/rollback

## Enforcement split
The frontend renders role-appropriate navigation and pages
(`Sidebar.jsx`, `App.jsx` route guards). All actual privilege decisions are
re-verified server-side on every request; the UI's role awareness is a
convenience layer, not the RBAC implementation itself.
