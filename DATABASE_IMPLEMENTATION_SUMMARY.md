# Database integration status

The finalized database schema is the source of truth for the full-stack application.

## Canonical setup

Initialize a new PostgreSQL database with these files, in order:

1. `database/schema/00_init.sql` — 15 tables, `vector(384)` columns, cosine HNSW indexes, constraints, and triggers.
2. `database/seeds/01_init_data.sql` — roles, permissions, five fixed departments, and starter categories.
3. `database/migrations/001_auth_password_and_feedback.sql` — idempotent password-hash and feedback permission compatibility migration.

Docker Compose mounts only those scripts. The other SQL files under `database/schema/` are overlapping historical fragments and must not be run as extra initialization steps.

## Application contract

- PostgreSQL 15+ with the `vector` extension enabled.
- `complaint_embeddings.embedding_vector` and `knowledge_document_chunks.chunk_embedding` are `vector(384)` and use cosine distance (`<=>`).
- Complaint statuses are `SUBMITTED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, and `REJECTED`.
- Resolution narratives are stored in `complaint_history.change_description`; there is no separate resolution table.
- `database/initialize.py` initializes an empty database or applies the idempotent seed and compatibility migration to a complete existing schema. It refuses to guess how to repair a partial schema.
- The API validates required PostgreSQL tables, columns, vector dimensions, HNSW indexes, roles, and departments at startup. It does not create production tables through SQLAlchemy.

## RAG data

Reference seed data does not include historical complaints or approved knowledge documents. After the local Compose stack is running, load the provided sample corpus with:

```powershell
docker compose run --rm ingest-knowledge
docker compose run --rm ingest-complaints
```

These importers generate `sentence-transformers/all-MiniLM-L6-v2` embeddings and support repeatable imports. Historical resolutions are preserved as complaint-history records; knowledge chunks are linked to the fixed departments.

## Verification status

The backend API and complaint workflow tests and the frontend production build pass in the current development environment. The Compose YAML parses, but a live PostgreSQL/pgvector and Docker Compose run has not yet been completed because the Docker CLI is unavailable in that environment. Follow the local startup and database verification instructions in [README.md](./README.md) once Docker Desktop is available.
