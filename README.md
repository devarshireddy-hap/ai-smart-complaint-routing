# CampusCare — Smart Complaint Routing

CampusCare is a full-stack campus complaint application with email/password and optional Google sign-in, role-based access, AI-assisted department/category/priority suggestions, pgvector retrieval, complaint tracking, and audit history.

## Stack and structure

- **Frontend:** React 18, Vite, Nginx
- **API:** Flask, SQLAlchemy, Flask-JWT-Extended
- **Database:** PostgreSQL 15 with pgvector
- **AI:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional vectors); optional Google Gemini suggestions require explicit user consent
- **Database schema:** `database/schema/00_init.sql` is canonical; `database/seeds/01_init_data.sql` provides roles, permissions, departments, and starter categories

```text
backend/                 Flask API, ORM mappings, admin bootstrap, API tests
ai/                      Embeddings, routing, RAG retrieval and ingestion
database/schema/         Canonical schema plus historical schema fragments
database/seeds/          Idempotent reference data
database/migrations/     Small forward migrations for existing databases
data/                    Sample complaint CSV and departmental guidance
frontend/                React/Vite interface and Nginx configuration
docker-compose.yml       Local PostgreSQL, API, frontend, optional ingestion jobs
```

The complaint statuses are `SUBMITTED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, and `REJECTED`. Resolution details are stored in `complaint_history`; there is no separate resolutions table. Historical complaint and knowledge embeddings use 384-dimensional cosine vectors.

## Run locally with Docker Desktop

### 1. Prerequisites

- Docker Desktop installed and running (the Compose command must be available in PowerShell)
- At least 8 GB of available memory recommended for the embedding model and containers

### 2. Configure local secrets

From the repository root in PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Change `DB_PASSWORD` to a long, URL-safe password using letters and numbers. Set `SECRET_KEY` and `JWT_SECRET_KEY` to different random values. The default values in `docker-compose.yml` are development-only; do not use them for a deployed environment. Keep `.env` private and never commit it.

Google OAuth is optional for local startup. To enable it, add the client ID and secret to `.env`, then add this exact authorized redirect URI to the Google OAuth client:

```text
http://localhost:3000/api/v1/auth/google/callback
```

Gemini is also optional and disabled by default. To enable it, set `ENABLE_GEMINI=true` and provide `GEMINI_API_KEY`; the UI requests consent before sending complaint text to Gemini.

### 3. Build and start the local stack

```powershell
docker compose up --build -d
docker compose ps
docker compose logs --tail 100 postgres api frontend
```

On a new, empty `postgres_data` volume, Docker initializes the database in this order:

1. `database/schema/00_init.sql` — canonical schema and pgvector indexes
2. `database/seeds/01_init_data.sql` — starter roles, permissions, departments, and categories
3. `database/migrations/001_auth_password_and_feedback.sql` — idempotent application compatibility migration

Do not run the other files under `database/schema/`; they are overlapping, older schema fragments. PostgreSQL runs initialization files only when its data directory is empty. If you already have a volume, do **not** delete it to fix startup problems. Apply the migration explicitly and inspect the existing schema first:

```powershell
docker compose exec -T postgres psql -U postgres -d complaint_routing -f /docker-entrypoint-initdb.d/03_app_migration.sql
```

If you changed `DB_USER` or `DB_NAME` in `.env`, use those values in the `psql` command.

### 4. Verify the services and database

The local app is at [http://localhost:3000](http://localhost:3000); the API health check is [http://localhost:5000/api/v1/health](http://localhost:5000/api/v1/health).

```powershell
Invoke-RestMethod http://localhost:5000/api/v1/health
docker compose exec postgres psql -U postgres -d complaint_routing -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker compose exec postgres psql -U postgres -d complaint_routing -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
docker compose exec postgres psql -U postgres -d complaint_routing -c "SELECT indexname, indexdef FROM pg_indexes WHERE indexname IN ('idx_complaint_embeddings_vector', 'idx_knowledge_chunks_embedding');"
```

Expected results include API status `ok`, extension `vector`, all 15 canonical tables, and HNSW indexes using `vector_cosine_ops`. The API checks required columns, the two `vector(384)` columns, vector indexes, and reference data during startup; a schema mismatch stops startup with a specific error.

### 5. Create the first administrator

Register a normal account in the UI, then bootstrap that account as the initial administrator:

```powershell
docker compose exec api python -m backend.seed_admin
```

Enter the email used during registration and a strong password. Sign out and sign back in to refresh the account's role. Administrators can promote users to department officers from **People & access**.

### 6. Load sample RAG data (optional but recommended)

The seeded database does not contain complaint history or knowledge chunks. These commands calculate embeddings and write the provided sample dataset and departmental guidance to PostgreSQL. The first embedding-model download can take a few minutes. The API image installs CPU-only PyTorch; local AI inference does not require downloading NVIDIA CUDA libraries.

```powershell
docker compose run --rm ingest-knowledge
docker compose run --rm ingest-complaints
```

Both importers are safe to rerun: knowledge chunks are replaced by source document, and historical complaints and embeddings are updated by source complaint ID. To inspect the process without writing data, run the scripts without `--write-to-database` from a Python environment with project dependencies installed.

Check the imported vector data:

```powershell
docker compose exec postgres psql -U postgres -d complaint_routing -c "SELECT COUNT(*) AS chunks, COUNT(chunk_embedding) AS embedded_chunks FROM knowledge_document_chunks;"
docker compose exec postgres psql -U postgres -d complaint_routing -c "SELECT COUNT(*) AS complaints, COUNT(embedding_vector) AS embedded_complaints FROM complaint_embeddings;"
```

The counts should be greater than zero after both ingestion commands complete. The complaint retriever only uses resolved historical records that have resolution text; knowledge retrieval uses active departmental chunks.

## Deploy to Render

The root `render.yaml` Blueprint defines a Render PostgreSQL database, the Flask API, and the React static site. It targets the `full-stack` branch and the Free/test tier selected for this initial deployment. Free Render Postgres is temporary and expires after 30 days; do not use it for important or durable complaint data. Choose a paid database plan before real production use.

1. Sign in to Render, choose **New + > Blueprint**, and connect `devarshireddy-hap/ai-smart-complaint-routing` on the `full-stack` branch.
2. Review the three resources before applying the Blueprint. The API creates the canonical schema, seeds reference data, and applies the compatibility migration on startup; this is safe for an empty database and checks before touching an existing one.
3. Wait for the API health check (`/api/v1/health`) and frontend deploy to succeed. The frontend discovers the API host through the Blueprint, and the API derives its allowed frontend origin from the static-site host.
4. For Google sign-in, add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to the API service's Render environment. Add this exact callback URI to the Google OAuth client's **Authorized redirect URIs**:

   ```text
   https://campuscare-api-dqr6.onrender.com/api/v1/auth/google/callback
   ```

   Keep `ENABLE_GEMINI=false` unless Gemini is intentionally enabled and `GEMINI_API_KEY` is configured. Never put production secrets in Git or chat.
5. Register your account, then open the API service's Render Shell and run `python -m backend.seed_admin` to promote it to the first administrator. Keep database connection strings private and do not commit local database backups.

The Blueprint generates separate random Flask and JWT secrets and enables secure cookies. Local `.env` values are not used by Render. Before importing existing data, back up the source database and follow a deliberate migration plan; this deployment creates a separate Render database and does not upload the local backup.

## Local development without the full container stack

For Python backend tests, use the isolated SQLite test configuration:

```powershell
$env:APP_ENV = "test"
$env:DATABASE_URL = "sqlite://"
python -m unittest backend.tests.test_api
```

For frontend-only development, keep the API running and use:

```powershell
cd frontend
npm ci
npm run dev
```

The Vite dev server uses `frontend/.env.example`'s local API URL. For Google sign-in, set `FRONTEND_URL=http://localhost:5173` in the root `.env` and use `GOOGLE_REDIRECT_URI=http://localhost:5000/api/v1/auth/google/callback`. The same callback works in Docker because the API is exposed on port 5000. This URI must exactly match an authorized redirect URI in Google Cloud. The Docker stack builds the frontend and API as separate services; Nginx serves the frontend and proxies `/api/` requests to Flask.

The first screen offers Student, Admin, and Department portals. Department users can create an account request, but it remains a Citizen account until an administrator assigns the Officer role and selected department in **People & access**. Admin access must be provisioned by an administrator. Department staff select their department at sign-in, and the API checks it against the account's assigned department. The admin table shows the effective portal type (Student, Department, or Admin); department requests are marked pending until approved. Complaints are routed to the AI-selected or explicitly selected department and appear in that department's queue, regardless of whether a student or admin submitted them. Admin account deletion anonymizes and disables the account while preserving complaint and audit history. The latest role/department or active-state change can be rolled back from **People & access** or **System activity**. Earlier changes can only be undone after newer changes are rolled back; anonymized deletions are not reversible. Complaint lists, dashboard summaries, and admin data refresh after changes, when the window regains focus, and every 30 seconds while open.

## Troubleshooting

- **`docker` is not recognized:** Start or install Docker Desktop, wait for its engine to become ready, then open a new PowerShell window and retry `docker compose version`.
- **API exits with a database schema error:** Check `docker compose logs api postgres`, confirm initialization completed, and apply the migration to an existing volume rather than deleting it.
- **PostgreSQL password authentication fails:** Ensure `.env` uses a URL-safe `DB_PASSWORD` and that the Compose containers were created with the same value.
- **Admin page is forbidden:** Bootstrap an administrator with `python -m backend.seed_admin`, then sign out and back in.
- **AI is in local matching mode:** Confirm the embedding model has downloaded and check API logs. The complaint workflow remains usable without Gemini; database vector retrieval requires the ingestion commands to have populated embeddings.

## Backup and persistence

The Compose `postgres_data` volume persists the database across container restarts. `docker compose down` keeps it. Do not use `docker compose down -v` unless you intentionally want to destroy the local database and all imported data. Automated file-based backup/restore is not supported for PostgreSQL; use PostgreSQL backup tools for operational backups.
