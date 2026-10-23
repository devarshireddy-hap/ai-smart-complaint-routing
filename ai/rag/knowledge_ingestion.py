"""Prepare and optionally ingest departmental knowledge documents."""

import argparse
import os
from pathlib import Path

import numpy as np
import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json

from ai.embeddings.embedding_generator import generate_embedding


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge_base"

EMBEDDING_DIMENSION = 384
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150

load_dotenv(PROJECT_ROOT / ".env")


def split_text(
    text: str,
    max_chars: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries."""
    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError("Invalid chunk size or overlap.")

    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))

        if end < len(text):
            lower_bound = start + max_chars // 2
            paragraph_end = text.rfind("\n\n", lower_bound, end)

            if paragraph_end != -1:
                end = paragraph_end
            else:
                word_end = text.rfind(" ", lower_bound, end)
                if word_end != -1:
                    end = word_end

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(start + 1, end - overlap)

    return chunks


def prepare_documents() -> list[dict]:
    """Read departmental documents and calculate their chunk embeddings."""
    if not KNOWLEDGE_DIR.is_dir():
        raise FileNotFoundError(
            f"Knowledge directory not found: {KNOWLEDGE_DIR}"
        )

    paths = sorted(KNOWLEDGE_DIR.glob("*.txt"))
    if not paths:
        raise FileNotFoundError(
            f"No .txt knowledge documents found in {KNOWLEDGE_DIR}"
        )

    prepared = []

    for path in paths:
        text = path.read_text(encoding="utf-8").strip()
        chunks = split_text(text)

        if not chunks:
            print(f"Skipping empty file: {path.name}")
            continue

        embedded_chunks = []

        for chunk in chunks:
            vector = np.asarray(
                generate_embedding(chunk),
                dtype=np.float32,
            )

            if vector.shape != (EMBEDDING_DIMENSION,):
                raise ValueError(
                    f"{path.name}: expected {EMBEDDING_DIMENSION} "
                    f"dimensions, received {vector.shape}"
                )

            if not np.isfinite(vector).all():
                raise ValueError(
                    f"{path.name}: embedding contains invalid values."
                )

            embedded_chunks.append((chunk, vector))

        prepared.append({
            "source": path.name,
            "department": path.stem.replace("_", " ").title(),
            "title": path.stem.replace("_", " ").title(),
            "chunks": embedded_chunks,
        })

        print(f"{path.name}: prepared {len(chunks)} chunks")

    if not prepared:
        raise ValueError("No non-empty knowledge documents were found.")

    return prepared


def ingest_knowledge_base(write_to_database: bool = False) -> None:
    """Preview the ingestion plan, or write chunks when explicitly enabled."""
    documents = prepare_documents()

    if not write_to_database:
        print("\nDRY RUN: embeddings prepared; nothing written to PostgreSQL.")
        print("Review the chunk counts before enabling database writes.")
        return

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Configure it in your local .env."
        )

    connection = psycopg2.connect(database_url, connect_timeout=5)

    try:
        register_vector(connection)

        for document in documents:
            with connection:
                with connection.cursor() as cursor:
                    # Serialize this script's document-ID allocation.
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(%s)",
                        (20261020,),
                    )

                    cursor.execute(
                        """
                        SELECT department_id
                        FROM departments
                        WHERE LOWER(department_name) = LOWER(%s)
                          AND is_active = TRUE
                        """,
                        (document["department"],),
                    )
                    department_row = cursor.fetchone()

                    if department_row is None:
                        raise ValueError(
                            "Active department not found: "
                            f"{document['department']}"
                        )

                    department_id = department_row[0]
                    source = document["source"]

                    # Reuse the document ID when re-ingesting the same file.
                    cursor.execute(
                        """
                        SELECT MIN(document_id)
                        FROM knowledge_document_chunks
                        WHERE department_id = %s
                          AND metadata->>'source' = %s
                        """,
                        (department_id, source),
                    )
                    existing_id = cursor.fetchone()[0]

                    if existing_id is None:
                        cursor.execute(
                            """
                            SELECT COALESCE(MAX(document_id), 0) + 1
                            FROM knowledge_document_chunks
                            """
                        )
                        document_id = cursor.fetchone()[0]
                    else:
                        document_id = existing_id

                        # Replace prior chunks for this source atomically.
                        cursor.execute(
                            """
                            DELETE FROM knowledge_document_chunks
                            WHERE department_id = %s
                              AND metadata->>'source' = %s
                            """,
                            (department_id, source),
                        )

                    for index, (chunk, vector) in enumerate(
                        document["chunks"]
                    ):
                        metadata = Json({
                            "source": source,
                            "department": document["department"],
                            "chunk_index": index,
                            "chunk_count": len(document["chunks"]),
                        })

                        cursor.execute(
                            """
                            INSERT INTO knowledge_document_chunks (
                                document_id,
                                department_id,
                                title,
                                chunk_text,
                                chunk_index,
                                chunk_embedding,
                                embedding_model,
                                metadata,
                                is_active
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                            """,
                            (
                                document_id,
                                department_id,
                                document["title"],
                                chunk,
                                index,
                                vector,
                                EMBEDDING_MODEL,
                                metadata,
                            ),
                        )

            print(
                f"Stored {len(document['chunks'])} chunks "
                f"for {source}"
            )

    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-to-database",
        action="store_true",
        help="Actually write chunks to PostgreSQL; otherwise preview only.",
    )
    args = parser.parse_args()

    try:
        ingest_knowledge_base(
            write_to_database=args.write_to_database
        )
    except (OSError, ValueError, RuntimeError, psycopg2.Error) as error:
        raise SystemExit(f"Ingestion failed: {error}") from error