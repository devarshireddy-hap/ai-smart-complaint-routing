
"""Import the sample complaint dataset into PostgreSQL + pgvector.

Default mode is a dry run. Use --write-to-database to write records.
Resolution text is preserved in complaint_history because the current
schema does not contain a dedicated resolution-text column.
"""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json

from ai.embeddings.embedding_generator import generate_embedding


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "data" / "complaints.csv"
SOURCE_DATASET = "data/complaints.csv"
IMPORT_USER_EMAIL = "historical-import@local.test"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}

load_dotenv(PROJECT_ROOT / ".env")


def required_text(value, column: str) -> str:
    """Return a non-empty string or raise a useful validation error."""
    if pd.isna(value):
        raise ValueError(f"Missing value in required column: {column}")

    value = str(value).strip()
    if not value:
        raise ValueError(f"Empty value in required column: {column}")

    return value


def make_title(description: str) -> str:
    """Derive a title that fits the complaints.title column."""
    normalized = " ".join(description.split())

    if len(normalized) <= 255:
        return normalized

    prefix = normalized[:252]
    if " " in prefix:
        prefix = prefix.rsplit(" ", 1)[0]

    return prefix + "..."


def prepare_records() -> list[dict]:
    """Validate CSV records and generate embeddings without database writes."""
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Dataset not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, dtype={"complaint_id": str})

    required_columns = {
        "complaint_id",
        "complaint_text",
        "department",
        "category",
        "priority",
        "resolution",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")

    if df.empty:
        raise ValueError("The complaint dataset is empty.")

    records = []
    seen_source_ids = set()

    for row_number, row in df.iterrows():
        source_id = required_text(
            row["complaint_id"], "complaint_id"
        )

        if source_id in seen_source_ids:
            raise ValueError(f"Duplicate source complaint ID: {source_id}")
        seen_source_ids.add(source_id)

        description = required_text(
            row["complaint_text"], "complaint_text"
        )
        department = required_text(row["department"], "department")
        category = required_text(row["category"], "category")
        priority = required_text(row["priority"], "priority").upper()

        if priority not in VALID_PRIORITIES:
            raise ValueError(
                f"Row {row_number + 2}: unsupported priority {priority!r}"
            )

        resolution_value = row["resolution"]
        resolution = (
            "" if pd.isna(resolution_value)
            else str(resolution_value).strip()
        )

        title = make_title(description)

        # Match the text construction used by the database retriever:
        # title + a space + description.
        embedding_text = f"{title} {description}"
        vector = np.asarray(
            generate_embedding(embedding_text),
            dtype=np.float32,
        )

        if vector.shape != (EMBEDDING_DIMENSION,):
            raise ValueError(
                f"Source complaint {source_id}: expected "
                f"{EMBEDDING_DIMENSION} dimensions, got {vector.shape}"
            )

        if not np.isfinite(vector).all():
            raise ValueError(
                f"Source complaint {source_id}: embedding is not finite."
            )

        records.append({
            "source_id": source_id,
            "title": title,
            "description": description,
            "department": department,
            "category": category,
            "priority": priority,
            "resolution": resolution,
            "embedding": vector,
        })

    return records


def write_records(records: list[dict]) -> None:
    """Insert or update imported complaints, resolutions, and embeddings."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing from the local .env file."
        )

    inserted = 0
    updated = 0
    new_categories = 0

    connection = psycopg2.connect(
        database_url,
        connect_timeout=5,
    )

    try:
        register_vector(connection)

        # All imported records are committed together. If one fails,
        # this transaction rolls back instead of leaving a partial import.
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (
                        email, name, user_type, is_active
                    )
                    VALUES (%s, %s, 'WORKING_STAFF', TRUE)
                    ON CONFLICT (email) DO UPDATE
                    SET name = EXCLUDED.name,
                        user_type = EXCLUDED.user_type,
                        is_active = TRUE
                    RETURNING user_id
                    """,
                    (
                        IMPORT_USER_EMAIL,
                        "Historical Dataset Import",
                    ),
                )
                import_user_id = cursor.fetchone()[0]

                for record in records:
                    # Resolve the department by name, never by assumed ID.
                    cursor.execute(
                        """
                        SELECT department_id
                        FROM departments
                        WHERE UPPER(department_name) = UPPER(%s)
                          AND is_active = TRUE
                        """,
                        (record["department"],),
                    )
                    department_row = cursor.fetchone()

                    if department_row is None:
                        raise ValueError(
                            "Active department not found: "
                            f"{record['department']}"
                        )

                    department_id = department_row[0]

                    # Preserve the dataset's category names exactly.
                    cursor.execute(
                        """
                        INSERT INTO categories (
                            category_name,
                            description,
                            department_id,
                            is_active
                        )
                        VALUES (%s, %s, %s, TRUE)
                        ON CONFLICT (category_name, department_id)
                        DO NOTHING
                        """,
                        (
                            record["category"],
                            "Category imported from the development dataset.",
                            department_id,
                        ),
                    )
                    new_categories += cursor.rowcount

                    cursor.execute(
                        """
                        SELECT category_id
                        FROM categories
                        WHERE category_name = %s
                          AND department_id = %s
                        """,
                        (record["category"], department_id),
                    )
                    category_row = cursor.fetchone()

                    if category_row is None:
                        raise ValueError(
                            "Could not resolve category "
                            f"{record['category']!r} for "
                            f"{record['department']!r}"
                        )

                    category_id = category_row[0]

                    # Use the history marker to find a previous import
                    # of this exact source record, making reruns idempotent.
                    cursor.execute(
                        """
                        SELECT c.complaint_id, h.history_id
                        FROM complaint_history AS h
                        JOIN complaints AS c
                          ON c.complaint_id = h.complaint_id
                        WHERE h.change_type = 'DATASET_IMPORT'
                          AND h.new_values->>'source_dataset' = %s
                          AND h.new_values->>'source_complaint_id' = %s
                        ORDER BY h.history_id DESC
                        LIMIT 1
                        """,
                        (SOURCE_DATASET, record["source_id"]),
                    )
                    existing = cursor.fetchone()

                    status = (
                        "RESOLVED" if record["resolution"] else "SUBMITTED"
                    )
                    resolved_at = (
                        "now" if record["resolution"] else None
                    )

                    if existing:
                        complaint_id, history_id = existing

                        cursor.execute(
                            """
                            UPDATE complaints
                            SET user_id = %s,
                                title = %s,
                                description = %s,
                                department_id = %s,
                                category_id = %s,
                                priority = %s,
                                status = %s,
                                resolved_at = CASE
                                    WHEN %s THEN COALESCE(
                                        resolved_at, CURRENT_TIMESTAMP
                                    )
                                    ELSE NULL
                                END,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE complaint_id = %s
                            """,
                            (
                                import_user_id,
                                record["title"],
                                record["description"],
                                department_id,
                                category_id,
                                record["priority"],
                                status,
                                bool(record["resolution"]),
                                complaint_id,
                            ),
                        )
                        updated += 1
                    else:
                        cursor.execute(
                            """
                            INSERT INTO complaints (
                                user_id, title, description,
                                department_id, category_id,
                                priority, status, resolved_at
                            )
                            VALUES (
                                %s, %s, %s, %s, %s, %s, %s,
                                CASE WHEN %s
                                     THEN CURRENT_TIMESTAMP
                                     ELSE NULL
                                END
                            )
                            RETURNING complaint_id
                            """,
                            (
                                import_user_id,
                                record["title"],
                                record["description"],
                                department_id,
                                category_id,
                                record["priority"],
                                status,
                                bool(record["resolution"]),
                            ),
                        )
                        complaint_id = cursor.fetchone()[0]
                        history_id = None
                        inserted += 1

                    history_values = Json({
                        "source_dataset": SOURCE_DATASET,
                        "source_complaint_id": record["source_id"],
                        "resolution": record["resolution"] or None,
                    })

                    change_description = (
                        record["resolution"]
                        or "Imported from the sample complaint dataset."
                    )

                    if history_id is None:
                        cursor.execute(
                            """
                            INSERT INTO complaint_history (
                                complaint_id, changed_by, change_type,
                                changed_field, change_description, new_values
                            )
                            VALUES (%s, %s, 'DATASET_IMPORT', 'resolution', %s, %s)
                            """,
                            (
                                complaint_id,
                                import_user_id,
                                change_description,
                                history_values,
                            ),
                        )
                    else:
                        cursor.execute(
                            """
                            UPDATE complaint_history
                            SET changed_by = %s,
                                changed_field = 'resolution',
                                change_description = %s,
                                new_values = %s
                            WHERE history_id = %s
                            """,
                            (
                                import_user_id,
                                change_description,
                                history_values,
                                history_id,
                            ),
                        )

                    cursor.execute(
                        """
                        INSERT INTO complaint_embeddings (
                            complaint_id, embedding_vector, embedding_model
                        )
                        VALUES (%s, %s, %s)
                        ON CONFLICT (complaint_id) DO UPDATE
                        SET embedding_vector = EXCLUDED.embedding_vector,
                            embedding_model = EXCLUDED.embedding_model,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (
                            complaint_id,
                            record["embedding"],
                            EMBEDDING_MODEL,
                        ),
                    )

        print("Database import committed successfully.")
        print("New complaints:", inserted)
        print("Existing complaints updated:", updated)
        print("New category labels added:", new_categories)
        print("Complaint embeddings written:", len(records))

    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare or import the sample historical complaints."
    )
    parser.add_argument(
        "--write-to-database",
        action="store_true",
        help="Write the records to PostgreSQL. Without this flag, run a dry run.",
    )
    args = parser.parse_args()

    try:
        records = prepare_records()

        print(f"Dataset: {CSV_PATH}")
        print(f"Validated complaints: {len(records)}")
        print(
            "Departments:",
            ", ".join(sorted({r["department"] for r in records})),
        )
        print(
            "Distinct department/category pairs:",
            len({(r["department"], r["category"]) for r in records}),
        )
        print(
            "Records with resolution text:",
            sum(bool(r["resolution"]) for r in records),
        )

        if not args.write_to_database:
            print("\nDRY RUN: no database records were written.")
            print("Review the summary before enabling database writes.")
            return

        write_records(records)

    except (OSError, ValueError, RuntimeError, psycopg2.Error) as error:
        raise SystemExit(f"Historical complaint import failed: {error}") from error


if __name__ == "__main__":
    main()
