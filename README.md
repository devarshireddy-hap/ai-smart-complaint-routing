# CampusCare — AI Smart Complaint Routing

CampusCare is a full-stack campus complaint workflow: users submit a concern, local AI recommends a department/category/priority and searches past examples and department guidance, and authorized staff work the complaint through a tracked resolution.

## What is in this repository now

- React + Vite web app with sign-in, complaint submission and tracking, AI suggestions, officer queue, admin user/role management, audit history, rollback and SQLite backup/restore screens.
- Flask REST API with password hashing, cookie-based JWT authentication and CSRF protection, optional Google OAuth, server-enforced permissions, complaint history and audit records.
- SQLAlchemy data model for accounts, roles/permissions, departments/categories, complaints, feedback, audit/history/rollback, backups, historical complaints, complaint embeddings and knowledge chunks.
- Database schema reference and ER diagram describing the current application models are in [`database/`](database/README.md) and [`docs/database/`](docs/database/database_design.md).
- Sentence Transformers `all-MiniLM-L6-v2` when available; an explicit local example-matching fallback otherwise. The system suggests rather than automatically enforces AI decisions.
- SQLite for the lowest-friction local demo; PostgreSQL 16 + pgvector through Docker Compose or `DATABASE_URL`.

## Quick start on Windows

Use two terminals from the repository root. The local setup below uses SQLite;
Docker is only needed for the PostgreSQL option.

1. Create the Python environment and install dependencies:

   ```powershell
   py -3.12 --version
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   ```

   Python 3.12 and Node.js 20 or newer are required. If `py -3.12 --version`
   fails, install Python 3.12 and enable the Python launcher before continuing.
   Before starting the frontend, check Node.js with `node --version`. If that
   command is not found, install the Node.js LTS release from
   <https://nodejs.org/> with the option to add Node.js to `PATH`, then close
   and reopen PowerShell.

2. Edit `.env`. Set different random values for `SECRET_KEY` and `JWT_SECRET_KEY`.
   SQLite is the default; Google sign-in and Gemini are optional and can stay
   blank/disabled. Do not replace an existing `.env` containing your local
   configuration.

3. Create the first Admin interactively (password is not echoed or stored in source):

   ```powershell
   python -m backend.seed_admin
   ```

4. Start the API:

   ```powershell
   python -m backend.app
   ```

   Health check: <http://localhost:5000/api/v1/health>

5. In another terminal, start the frontend:

   ```powershell
   cd frontend
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   npm.cmd install
   npm.cmd run dev
   ```

   Open <http://localhost:5173>. New accounts self-register as Citizens. Use the first Admin account to promote a registered account to Officer and select a department.

   In PowerShell, use `npm.cmd` rather than `npm` if script execution is
   restricted; this avoids changing the machine's execution policy.

   If PowerShell blocks environment activation, run
   `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and
   `.\.venv\Scripts\python.exe -m backend.app` from the repository root
   instead of activating the environment.

The first AI request loads `sentence-transformers/all-MiniLM-L6-v2`; the initial model download can take time and needs network access. If the model cannot be loaded because of a missing dependency, unavailable model files, or network failure, the response explicitly labels the local example-matching fallback. Gemini is disabled by default. To enable it, set `ENABLE_GEMINI=true` and `GEMINI_API_KEY`; users must separately opt in for each complaint, and the UI discloses that complaint text and retrieved context will be sent to Google.

## PostgreSQL / Docker Compose

Docker Compose runs PostgreSQL with pgvector, the Flask API and the production-built React app:

1. Set `POSTGRES_PASSWORD`, `SECRET_KEY`, and `JWT_SECRET_KEY` in `.env` to strong unique values. Set `FRONTEND_URL=http://localhost:8080`.
2. Run `docker compose up --build`.
3. Create the initial administrator in the API container:

   ```powershell
   docker compose exec api python -m backend.seed_admin
   ```

4. Open <http://localhost:8080>.

The API installs the pgvector extension and creates its tables/indexes on first startup. It imports the 50 CSV examples into a separate historical-complaint table, and the first model-backed analysis creates normalized embeddings for the examples and five knowledge documents. HNSW cosine indexes are used for semantic search over persisted historical/live complaints and knowledge. Automated backup/restore endpoints currently support SQLite only; for PostgreSQL, use and rehearse `pg_dump`/`pg_restore` with an operational retention policy.

The current ORM schema is documented in [`docs/database/database_design.md`](docs/database/database_design.md), with its ER diagram in [`docs/database/ER_DIAGRAM.md`](docs/database/ER_DIAGRAM.md). SQLAlchemy models are authoritative; [`database/schema/00_init.sql`](database/schema/00_init.sql) is a PostgreSQL reference matching those models, not a migration that the app executes. The SQL scripts on the separate GitHub `database` branch use a different schema and should not be run against this application database.

## Demo walkthrough

1. Register as a student with a 10+ character password.
2. Submit a concern such as: **“Water is leaking from a pipe behind the east residence hall.”**
3. Review the Plumbing recommendation, category, priority, possible duplicate signal and suggested next step; change the department if the suggestion is wrong, then submit.
4. Open the Admin → People & access page and promote a second account to Officer, choosing Plumbing.
5. Sign in as that Officer. The queue is limited to Plumbing complaints. Move the concern to In progress, then Resolved with a resolution note.
6. Sign back in as the Citizen to view the timeline, resolution, and reopen a resolved concern if it still needs attention.
7. As Admin, inspect System activity, create/download a SQLite backup, or roll back a selected recorded change. Restore requires typing `RESTORE` and creates a pre-restore copy.

## Example API shape

`POST /api/v1/ai/analyze` (authenticated):

```json
{
  "description": "Water is leaking from a pipe behind the east residence hall."
}
```

Illustrative response shape; the actual match arrays and model warning depend on local data/model availability:

```json
{
  "department": "PLUMBING",
  "category": "Water Leakage",
  "priority": "HIGH",
  "duplicate": false,
  "similar_complaints": [],
  "knowledge_documents": [],
  "suggested_resolution": "Suggested from a similar historical case: ...",
  "model": "sentence-transformers",
  "warning": null
}
```

`POST /api/v1/complaints` accepts `title`, `description`, optional `location`, and optional department override. It returns a generated reference, AI metadata and status `SUBMITTED`. Mutating authenticated API calls use the HttpOnly JWT cookie plus the CSRF header provided by the frontend.

## Access model

| Role | Effective access |
| --- | --- |
| Citizen | Create concerns, view only their own, reopen resolved/closed reports, leave feedback after resolution |
| Officer | View and progress complaints only in their assigned department |
| Admin | Cross-department visibility, user/role management, audit access, complaint rollback and database recovery actions |

Signup never accepts an authorization role from the browser. Google sign-in creates a Citizen by default; it does not grant Admin. The API checks permissions on every protected route; UI hiding is not relied upon for authorization.

## Configuration and security notes

- Passwords use Werkzeug's scrypt password hash; Google account passwords are never collected.
- JWTs are stored in HttpOnly cookies with CSRF protection. Set `COOKIE_SECURE=true` and configure HTTPS in deployment. Use separate production secrets and restrict CORS to the actual frontend origin.
- OAuth and Gemini credentials stay in the backend environment. Do not put them in Vite `VITE_*` variables or commit a real `.env`.
- Gemini generation is optional, disabled by default, and requires an explicit per-complaint consent checkbox. The local RAG-grounded suggestion remains available without consent or an external API key.
- A new account can never self-select an Officer/Admin role. Bootstrap the first Admin through the interactive script.
- AI suggestions are not decisions. The sample CSV is small and is not evidence of production accuracy; review and measure on representative, consented institutional data before operational use.
- Database backup/restore endpoints are deliberately Admin-only and SQLite-only. PostgreSQL backup/restore must be configured operationally outside the web API.
- The app creates tables on startup for a clean demo database. Production schema changes should use reviewed migrations rather than relying on `create_all`.
- Uploads, notifications, public deployment, production monitoring/rate-limits, and a formally evaluated model are not part of this demo implementation.

## Tests

Run backend tests with:

```powershell
python -m unittest backend.tests.test_api
```

Build the frontend with:

```powershell
cd frontend
npm run build
```
