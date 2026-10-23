"""Initialize an empty PostgreSQL database with the canonical schema and seed."""

import os
from pathlib import Path

import psycopg2
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema" / "00_init.sql"
SEED_PATH = PROJECT_ROOT / "database" / "seeds" / "01_init_data.sql"
MIGRATION_PATH = PROJECT_ROOT / "database" / "migrations" / "001_auth_password_and_feedback.sql"
REQUIRED_TABLES = {
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "departments",
    "categories",
    "complaints",
    "complaint_history",
    "complaint_embeddings",
    "knowledge_document_chunks",
    "audit_logs",
    "backup_records",
    "rollback_records",
    "feedback",
}


def initialize_database() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to initialize PostgreSQL.")
    database_url = make_url(database_url).set(drivername="postgresql").render_as_string(
        hide_password=False
    )

    with psycopg2.connect(database_url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_type = 'BASE TABLE'
                """
            )
            existing_tables = {row[0] for row in cursor.fetchall()}

            if not existing_tables:
                cursor.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
                print("Created the canonical database schema.")
            else:
                missing_tables = REQUIRED_TABLES - existing_tables
                if missing_tables:
                    raise RuntimeError(
                        "Refusing to initialize a partially populated database. "
                        "Missing tables: " + ", ".join(sorted(missing_tables))
                    )
                print("Canonical tables already exist; schema was not recreated.")

            cursor.execute(SEED_PATH.read_text(encoding="utf-8"))
            cursor.execute(MIGRATION_PATH.read_text(encoding="utf-8"))
        connection.commit()

    print("Reference seed data is ready.")


if __name__ == "__main__":
    initialize_database()
