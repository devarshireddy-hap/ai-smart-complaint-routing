# Security Decisions — Zero Trust

Source: Final PSD §22.

## Principle
"Never trust a request merely because it was authenticated earlier."
Every protected action re-verifies: Google identity → session/token →
role → permission → resource access → action permitted.

## How the frontend respects this
- The frontend never caches a "yes you can do this" decision beyond the
  current render. `AuthContext.role` is used only to decide what to *show*;
  every actual mutation (status update, resolution, feedback, admin action)
  still goes through the backend, which re-checks independently.
- `ProtectedRoute` re-evaluates on every navigation rather than trusting a
  value set once at login.
- A session that becomes invalid mid-use (expired, revoked, or the cookie
  cleared) is discovered the next time any API call returns 401 — the
  `ApiError` produced by `services/api.js` is what pages use to redirect
  back to `/login`, not a client-side timer.
- The officer department-portal selection (see `access_control.md`) is
  explicitly excluded from anything resembling a trust decision — it is
  never checked by the backend and grants no access on its own.

## Network location is not trust
The frontend does not assume requests from `localhost` or an internal
network are safer; the same `credentials: 'include'` + backend
verification path is used regardless of environment.
