# Database files

CampusCare's executable schema is defined by the SQLAlchemy models in
[`backend/models.py`](../backend/models.py). When the API starts, it creates the
tables with `db.create_all()` and seeds roles, permissions, the five supported
departments, categories from the sample dataset, and historical complaint rows.
The first model-backed analysis adds the available vector embeddings.

`schema/00_init.sql` is a PostgreSQL/pgvector schema reference that follows the
current application models. It is not executed by Docker Compose or by the API.
Use the models as the source of truth when changing the application schema; the
SQL file and database documentation should be updated to match.

The SQL scripts from the repository's separate `database` branch are not
drop-in compatible with this application: they use integer primary keys, a
different user/role layout, and different complaint status values. Do not run
those legacy scripts against a CampusCare database.

## Database choices

- Local development defaults to SQLite at `instance/complaints.db`.
- Docker Compose uses PostgreSQL 16 with pgvector. The database is named
  `campuscare` by default and its data persists in the `postgres_data` Docker
  volume.
- PostgreSQL semantic search uses 384-dimensional
  `sentence-transformers/all-MiniLM-L6-v2` vectors and HNSW cosine indexes.
- SQLite stores vectors as JSON and performs local similarity comparisons.

For Docker PostgreSQL, inspect tables from the repository root:

```powershell
docker compose exec db psql -U campuscare -d campuscare
```

Then use `\dt` to list tables, `\d complaints` to inspect a table, and `\q` to
exit. A database GUI can connect to a host-published PostgreSQL port if one is
configured; the default Compose file does not publish the database port.

For local SQLite, open `instance/complaints.db` using DB Browser for SQLite or
another SQLite client.

## Schema changes

`db.create_all()` is suitable for a clean demo database; it does not migrate
existing tables when model columns change. Back up existing data before any
schema change. Production deployments should adopt reviewed, versioned
migrations before applying model changes to an existing database.
