# PRACTICE MODE — click through every dashboard with no backend

Practice Mode is a pretend backend that lives entirely inside the frontend
(`src/mocks/`). It exists purely so you can visually verify every page,
dashboard, and role before Milan's Flask backend and Devarshi's database
are ready. It is completely separate from the real code path.

## Turn it on
In `frontend/.env`, set:
```
VITE_MOCK_MODE=true
```
Restart `npm run dev` after changing it (Vite only reads `.env` at startup).

## What changes
- The Login page shows three buttons ("Sign in as Student", "...Officer",
  "...Admin") instead of "Continue with Google".
- Every API call (`services/api.js`) is transparently swapped for a fake
  version (`src/mocks/mockApi.js`) that returns realistic sample data —
  6 sample complaints across all 5 departments and every status/priority,
  3 sample users, and 4 sample audit log entries (`src/mocks/mockData.js`).
- Data you create (a new complaint, a status change, a role change)
  persists in the browser's `sessionStorage` for that tab, so it feels
  real while you're clicking around, and resets when you close the tab.

## What it's for
Verifying: does the Student dashboard show complaints? Does creating a
complaint work? Does the Officer dashboard let you move a status forward?
Does the Admin dashboard show analytics, let you change a role, view audit
logs, and trigger backup/restore/rollback confirmations? All of that,
without needing Flask or PostgreSQL running at all.

## What it does NOT verify
- Whether the real backend's field names, response shapes, or endpoints
  actually match what the frontend expects (see `INTEGRATION_CHECKLIST.md`)
- Real authentication/authorization security — Practice Mode has none,
  by design, since it's not talking to a real server
- Anything involving the real AI/RAG pipeline — the "AI analysis" you see
  is hand-written sample text, not a real Gemini response

## Turn it off
Set `VITE_MOCK_MODE=false` (or delete the line) and restart `npm run dev`
once the real backend is running. **Always leave it off for any real
deployment** — the Dockerfile does not set this variable, so production
builds are unaffected by default.
