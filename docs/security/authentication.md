# Security Decisions — Authentication

Source: Final PSD §13, §14; Master Doc §30.

## Decision
Google OAuth 2.0 / OpenID Connect is the **only** authentication mechanism.
There is no local password login, and none is planned. The application
never asks for or stores a password.

## Flow
1. Browser → `GET /auth/google/start` (backend, public)
2. Google's consent screen
3. Google → `GET /auth/google/callback` (backend, public) with an
   authorization code
4. Backend exchanges the code, verifies the ID token, looks up or creates
   the user by Google's stable `google_subject` (never by email alone),
   and establishes a secure server-side session
5. Backend redirects the browser to the frontend's `/auth/callback`
6. Frontend calls `GET /me` to confirm the session and read the user's role

## Frontend responsibilities
- `src/pages/Login.jsx` only links to the backend's `/auth/google/start` —
  it never calls Google directly and never handles a client ID/secret
- `src/pages/AuthCallback.jsx` re-checks `/me` rather than trusting any
  query parameter the redirect might carry
- `src/services/api.js` sends `credentials: 'include'` on every request so
  the session cookie is attached
- No access token or session identifier is ever placed in a URL, `localStorage`,
  or a log statement from frontend code

## What the frontend explicitly does NOT do
- Store or transmit a Google client secret
- Attempt to validate the Google ID token itself (the backend does this)
- Persist any authentication state outside of the backend session and the
  in-memory `AuthContext`
