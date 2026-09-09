# Security Decisions — Authorization

Source: Final PSD §4, §14; Master Doc §33–34.

## Decision
Authorization is RBAC (role-based) plus resource-level checks, enforced
**exclusively on the backend**. The frontend's role checks
(`ProtectedRoute.jsx`) and conditional rendering exist only to give users a
coherent experience — hiding a button or redirecting away from a page is
never treated as a security control.

## Backend is authoritative
Every protected backend endpoint independently re-verifies:
`Identity → Role → Resource ownership/assignment → Permission → Business
rule → Transaction → Audit` (Final PSD §29). The frontend assumes nothing
about what it's allowed to do beyond what each API response actually
returns; a 403 from the backend is always respected and surfaced to the
user (see `ComplaintDetails.jsx`'s `notFoundOrForbidden` handling).

## Frontend-side authorization touchpoints
| Boundary | Frontend behavior | Real enforcement |
|---|---|---|
| Route access by role | `ProtectedRoute` redirects to `/forbidden` | Backend checks role on every call regardless of which page rendered |
| Complaint ownership (student) | UI never exposes another student's complaint link | Backend returns 403/404 if a student edits the URL directly |
| Officer assignment scope | Officer dashboard shows only what `GET /complaints` returns | Backend filters the list server-side to the officer's assignments |
| Admin-only actions | Buttons for role change, rollback, backup/restore only render for ADMIN | Backend rejects non-admin callers independently |
| Officer department portal | Frontend-only display/routing convenience (see `docs/security/access_control.md`) | Backend's assignment-based scoping is unaffected by the selection |

## What must never happen
- No component computes "is this allowed" and then calls a privileged
  endpoint without the backend performing its own check
- No admin action executes directly against the database, pgvector, or the
  LLM from the browser
