
"""
PostgreSQL + pgvector retrieval for the complaint-routing RAG system.

This module supplements the existing local-file retriever.
It does not replace ai/rag/retriever.py.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import RealDictCursor

from ai.embeddings.embedding_generator import generate_embedding


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

TOP_K = 5
EMBEDDING_DIMENSION = 384


def _validate_top_k(top_k: int) -> int:
    """Ensure the SQL LIMIT value is valid."""
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer.")
    return top_k


def _make_embedding(text: str) -> np.ndarray:
    """Generate and validate a query embedding."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Query text must be a non-empty string.")

    embedding = np.asarray(
        generate_embedding(text.strip()),
        dtype=np.float32,
    )

    if embedding.shape != (EMBEDDING_DIMENSION,):
        raise ValueError(
            f"Expected a {EMBEDDING_DIMENSION}-dimensional embedding; "
            f"received shape {embedding.shape}."
        )

    if not np.isfinite(embedding).all():
        raise ValueError("Embedding contains invalid numeric values.")

    return embedding


def _get_connection():
    """Open PostgreSQL and register pgvector's NumPy adapter."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Add it to your local .env file."
        )

    connection = psycopg2.connect(
        database_url,
        connect_timeout=5,
    )

    try:
        register_vector(connection)
    except Exception:
        connection.close()
        raise

    return connection


def retrieve_similar_complaints(
    complaint: str,
    department: Optional[str] = None,
    top_k: int = TOP_K,
) -> List[Dict[str, Any]]:
    """
    Retrieve complaints ranked by cosine similarity.

    The current schema does not store a dedicated resolution narrative,
    so this function does not fabricate one.
    """
    top_k = _validate_top_k(top_k)
    query_embedding = _make_embedding(complaint)

    sql = """
        SELECT
            c.complaint_id,
            CONCAT_WS(
                ' ',
                NULLIF(c.title, ''),
                NULLIF(c.description, '')
            ) AS complaint_text,
            d.department_name AS department,
            cat.category_name AS category,
            c.priority,
            c.status,
            c.resolved_at,
            hist.resolution,
            1 - (ce.embedding_vector <=> %s) AS similarity
        FROM complaint_embeddings AS ce
        JOIN complaints AS c
            ON c.complaint_id = ce.complaint_id
        LEFT JOIN departments AS d
            ON d.department_id = c.department_id
        LEFT JOIN categories AS cat
            ON cat.category_id = c.category_id
        LEFT JOIN LATERAL (
            SELECT COALESCE(
                NULLIF(h.new_values->>'resolution', ''),
                NULLIF(h.change_description, '')
            ) AS resolution
            FROM complaint_history AS h
            WHERE h.complaint_id = c.complaint_id
              AND h.change_type = 'DATASET_IMPORT'
              AND h.new_values->>'source_dataset' = 'data/complaints.csv'
            ORDER BY h.history_id DESC
            LIMIT 1
        ) AS hist ON TRUE
        WHERE ce.embedding_vector IS NOT NULL
          AND COALESCE(c.is_duplicate, FALSE) = FALSE
    """

    parameters = [query_embedding]

    if department:
        sql += " AND UPPER(d.department_name) = UPPER(%s)"
        parameters.append(department)

    sql += """
        ORDER BY ce.embedding_vector <=> %s
        LIMIT %s
    """
    parameters.extend([query_embedding, top_k])

    connection = _get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, parameters)
            rows = cursor.fetchall()

        results = []

        for row in rows:
            item = dict(row)
            resolved_at = item.get("resolved_at")

            item["resolved_at"] = (
                resolved_at.isoformat() if resolved_at else None
            )
            item["similarity"] = float(item["similarity"])

            results.append(item)

        return results

    finally:
        connection.close()


def retrieve_knowledge_documents(
    complaint: str,
    department: Optional[str] = None,
    top_k: int = TOP_K,
) -> List[Dict[str, Any]]:
    """Retrieve active knowledge chunks ranked by cosine similarity."""
    top_k = _validate_top_k(top_k)
    query_embedding = _make_embedding(complaint)

    sql = """
        SELECT
            k.chunk_id,
            k.document_id,
            k.title,
            k.chunk_text,
            k.chunk_index,
            k.metadata,
            d.department_name AS department,
            1 - (k.chunk_embedding <=> %s) AS similarity
        FROM knowledge_document_chunks AS k
        JOIN departments AS d
            ON d.department_id = k.department_id
        WHERE k.is_active = TRUE
          AND k.chunk_embedding IS NOT NULL
    """

    parameters = [query_embedding]

    if department:
        sql += " AND UPPER(d.department_name) = UPPER(%s)"
        parameters.append(department)

    sql += """
        ORDER BY k.chunk_embedding <=> %s
        LIMIT %s
    """
    parameters.extend([query_embedding, top_k])

    connection = _get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, parameters)
            rows = cursor.fetchall()

        results = []

        for row in rows:
            item = dict(row)
            metadata = item.get("metadata") or {}

            if not isinstance(metadata, dict):
                metadata = {}

            item["source"] = metadata.get(
                "source",
                f"document:{item['document_id']}",
            )
            item["text"] = item.pop("chunk_text")
            item["similarity"] = float(item["similarity"])

            results.append(item)

        return results

    finally:
        connection.close()


def retrieve_rag_information(
    complaint: str,
    department: Optional[str] = None,
    top_k: int = TOP_K,
) -> Dict[str, Any]:
    """Return both types of database-backed RAG context."""
    return {
        "similar_complaints": retrieve_similar_complaints(
            complaint=complaint,
            department=department,
            top_k=top_k,
        ),
        "knowledge_documents": retrieve_knowledge_documents(
            complaint=complaint,
            department=department,
            top_k=top_k,
        ),
    }


if __name__ == "__main__":
    test_complaint = (
        "There is a water pipe leak behind the hostel building."
    )

    try:
        result = retrieve_rag_information(
            complaint=test_complaint,
            department="Plumbing",
            top_k=TOP_K,
        )

        print("Similar complaints:", len(result["similar_complaints"]))
        print("Knowledge chunks:", len(result["knowledge_documents"]))

        for item in result["knowledge_documents"]:
            print(
                item["title"],
                f"similarity={item['similarity']:.4f}",
            )

    except (psycopg2.Error, RuntimeError) as error:
        print(f"Database retrieval could not run: {error}")
