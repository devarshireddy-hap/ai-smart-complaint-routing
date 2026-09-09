# Security Decisions — Google SSO

Source: Final PSD §13.

## Decision
Google is the sole identity provider. The frontend integrates with it
indirectly — it never embeds a Google client ID/secret or calls Google's
APIs directly; it only links to the backend's `/auth/google/start` and
trusts the backend's session afterward.

## Identity key
The backend keys users by `google_subject` (Google's stable subject
identifier), never by email alone, since email addresses can be reused or
changed. The frontend never uses email as a lookup key for anything
security-relevant either.

## Session, not token, on the frontend
Per the locked decision (server-side sessions, not JWT), the frontend holds
no access token in memory or storage — `AuthContext` only holds the
`GET /me` response (name, email, role). Every subsequent request relies on
the browser automatically attaching the session cookie
(`credentials: 'include'`).

## Transport
In production, the app assumes HTTPS end-to-end so the session cookie can
safely be `Secure`. Local development over `http://localhost` is the only
exception, matching standard browser cookie behavior for `localhost`.
