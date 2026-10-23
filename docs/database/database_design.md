# CampusCare Database Design

## Runtime architecture

The Flask API uses SQLAlchemy models in [`backend/models.py`](../../backend/models.py)
as the application schema. At startup, `db.create_all()` creates missing tables,
then the API seeds its base roles, permissions, five departments, dataset
categories, historical examples, and knowledge-document records.

The app supports two database backends:

| Mode | Database | Vector representation |
| --- | --- | --- |
| Local default | SQLite in `instance/complaints.db` | JSON arrays; local similarity |
| Docker Compose | PostgreSQL 16 with pgvector | `vector(384)` with HNSW cosine indexes |

The reference PostgreSQL DDL is in [`database/schema/00_init.sql`](../../database/schema/00_init.sql).
It is for inspection and manual schema reference; the API does not execute it.

## Entities

| Table | Purpose |
| --- | --- |
| `users` | Login identity, password hash or Google subject, account state, one role and optional department |
| `roles` | `CITIZEN`, `OFFICER`, and `ADMIN` role definitions |
| `permissions` | Permission names used by API route authorization |
| `role_permissions` | Many-to-many role-to-permission grants |
| `departments` | The five supported campus departments |
| `categories` | Department-specific complaint categories |
| `complaints` | Submitted complaint, current status, routing, AI metadata and resolution |
| `complaint_history` | State snapshots and notes for complaint timeline/rollback |
| `audit_logs` | Admin-visible audit activity |
| `feedback` | One reporter rating/comment per resolved complaint |
| `backup_records` | Metadata for SQLite backups and pre-restore copies |
| `rollback_records` | Records complaint rollback operations |
| `historical_complaints` | Imported sample cases used for AI recommendations |
| `knowledge_document_chunks` | Department knowledge text and optional embedding |
| `complaint_embeddings` | Optional embedding for a live complaint |

## Relationships and rules

- A user has one role through `users.role_id`. A role has many permissions through
  `role_permissions`. This is intentionally not the `user_roles` multi-role
  arrangement in the separate GitHub database branch.
- Officers have an assigned department. API authorization restricts their
  complaint access to that department.
- A complaint has a reporter, department, category, and status; an officer
  assignment is optional. Complaint status transitions and notes are recorded in
  `complaint_history`.
- Categories are unique within a department. Departments are seeded from a
  fixed set: Technical, Finance, Electrical, Plumbing, and Security.
- Status values are `SUBMITTED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`,
  `CLOSED`, and `REOPENED`. Priority values are `LOW`, `MEDIUM`, `HIGH`, and
  `URGENT`.
- Feedback is available to the reporting user after resolution and is unique per
  complaint/user pair.
- Embedding columns are 384-dimensional for
  `sentence-transformers/all-MiniLM-L6-v2`. In PostgreSQL, HNSW indexes use
  cosine distance. Embeddings may remain absent when the local model is
  unavailable.

## Schema history and compatibility

The GitHub `database` branch contains an earlier integer-ID schema and docs.
That schema has different user/role tables and does not match the current
application's UUID-string identifiers, single-role user model, or complaint
status values. Its scripts must not be run against this app database. The
database reference files in this workspace describe the current application
schema instead.

`db.create_all()` creates new tables but is not a migration system: it does not
alter existing tables after model changes. Back up data and use reviewed,
versioned migrations before evolving a deployed database. PostgreSQL automated
backup/restore through the web app is not implemented; use operational
`pg_dump`/`pg_restore`.
