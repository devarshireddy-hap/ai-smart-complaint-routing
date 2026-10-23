# Full-stack local readiness

This file tracks the current integration state; it is not a claim that PostgreSQL has already been run or that the system is production-ready.

## Implemented

- Flask API mapped to the finalized 15-table integer-ID PostgreSQL schema.
- Email/password authentication, optional Google OAuth, cookie-based JWT authentication with CSRF protection, and role/department authorization.
- Complaint submission, AI suggestions, department queue, status history, feedback, category management, and administrator audit views.
- 384-dimensional pgvector cosine retrieval for historical complaints and knowledge chunks.
- Repeatable historical complaint and knowledge-data ingestion commands.
- Docker Compose configuration for pgvector PostgreSQL, API, React/Nginx frontend, and optional ingestion jobs.
- Startup schema verification; production startup does not create ORM tables.

## Verified in the current development environment

- `python -m unittest backend.tests.test_api` — 5 tests pass using isolated SQLite test mode.
- `npm run build` — Vite production build succeeds.
- Python modules compile and `docker-compose.yml` parses as YAML.

## Still needs a local Docker runtime check

Docker Desktop / the Docker CLI is unavailable in the current execution environment, so the full PostgreSQL/pgvector Compose stack has not been started here. The following must be confirmed locally before calling the application runtime-ready:

1. Start the services with `docker compose up --build -d`.
2. Verify the API health endpoint and PostgreSQL extension, tables, and vector indexes.
3. Bootstrap the first administrator using `docker compose exec api python -m backend.seed_admin`.
4. Import sample RAG data using the commands in [README.md](./README.md).
5. Submit a complaint in the browser, progress it through resolution, and verify feedback and audit history.

Deployment configuration is intentionally deferred until the local application has been run and verified.
