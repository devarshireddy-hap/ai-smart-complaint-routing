"""
RAG pipeline.

Pipeline:
Complaint
    -> Retrieve similar historical complaints
    -> Retrieve department knowledge documents
    -> Build combined context
    -> Return AI-ready RAG result
"""

from typing import Dict, Optional

import os
from pathlib import Path

from dotenv import load_dotenv

from ai.rag.retriever import (
    retrieve_rag_information as retrieve_local_rag_information,
)
from ai.rag.database_retriever import (
    retrieve_rag_information as retrieve_database_rag_information,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TOP_K = 5
RAG_MODEL_NAME = "all-MiniLM-L6-v2"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def retrieve_rag_information(
    complaint: str,
    department: Optional[str] = None,
    top_k: int = DEFAULT_TOP_K,
) -> Dict:
    """Choose the local or database retriever from environment settings."""

    backend = os.getenv(
        "RAG_RETRIEVER_BACKEND", "local"
    ).strip().lower()

    if backend == "local":
        return retrieve_local_rag_information(
            complaint=complaint,
            department=department,
            top_k=top_k,
        )

    if backend == "database":
        return retrieve_database_rag_information(
            complaint=complaint,
            department=department,
            top_k=top_k,
        )

    raise ValueError(
        "RAG_RETRIEVER_BACKEND must be 'local' or 'database'."
    )


# ============================================================
# CONTEXT BUILDER
# ============================================================

def build_combined_rag_context(
    complaint: str,
    similar_complaints,
    knowledge_documents,
) -> str:
    """
    Build a combined context for the AI response.

    The context contains:
    1. The original complaint
    2. Similar historical complaints
    3. Their historical resolutions
    4. Relevant knowledge-base information
    """

    sections = []

    # --------------------------------------------------------
    # Original complaint
    # --------------------------------------------------------

    sections.append(
        "CURRENT COMPLAINT\n"
        f"{complaint}"
    )

    # --------------------------------------------------------
    # Historical complaints
    # --------------------------------------------------------

    if similar_complaints:

        historical_section = [
            "SIMILAR HISTORICAL COMPLAINTS"
        ]

        for item in similar_complaints:

            historical_section.append(
                "\n"
                f"Complaint ID: {item['complaint_id']}\n"
                f"Complaint: {item['complaint_text']}\n"
                f"Department: {item['department']}\n"
                f"Category: {item['category']}\n"
                f"Priority: {item['priority']}\n"
                f"Similarity: {item['similarity']:.4f}\n"
                f"Historical Resolution: "
                f"{item['resolution']}"
            )

        sections.append(
            "\n".join(historical_section)
        )

    # --------------------------------------------------------
    # Knowledge documents
    # --------------------------------------------------------

    if knowledge_documents:

        knowledge_section = [
            "KNOWLEDGE BASE DOCUMENTS"
        ]

        for document in knowledge_documents:

            knowledge_section.append(
                "\n"
                f"Source: {document['source']}\n"
                f"Department: "
                f"{document['department']}\n"
                f"Similarity: "
                f"{document['similarity']:.4f}\n"
                f"Content:\n"
                f"{document['text']}"
            )

        sections.append(
            "\n".join(knowledge_section)
        )

    return "\n\n" + "\n\n".join(sections)


# ============================================================
# SOURCE BUILDER
# ============================================================

def build_rag_sources(
    similar_complaints,
    knowledge_documents,
):
    """
    Build a unified source list for the final AI response.
    """

    sources = []

    for complaint in similar_complaints:

        sources.append(
            {
                "type": "historical_complaint",
                "source": (
                    f"complaint_"
                    f"{complaint['complaint_id']}"
                ),
                "similarity": (
                    complaint["similarity"]
                ),
            }
        )

    for document in knowledge_documents:

        sources.append(
            {
                "type": "knowledge_document",
                "source": document["source"],
                "similarity": document["similarity"],
            }
        )

    return sources


# ============================================================
# RAG PIPELINE
# ============================================================

def run_rag_pipeline(
    complaint: str,
    top_k: int = DEFAULT_TOP_K,
    department: Optional[str] = None,
) -> Dict:
    """
    Run the complete RAG retrieval pipeline.

    Args:
        complaint:
            New complaint text.

        top_k:
            Number of historical complaints and knowledge
            documents to retrieve.

        department:
            Predicted complaint department.

    Returns:
        Dictionary containing:
        - complaint
        - department
        - similar_complaints
        - knowledge_documents
        - retrieved_context
        - sources
        - model
    """

    # --------------------------------------------------------
    # Input validation
    # --------------------------------------------------------

    if not isinstance(complaint, str):
        raise ValueError(
            "complaint must be a string."
        )

    if not complaint.strip():
        raise ValueError(
            "complaint must be a non-empty string."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than zero."
        )

    # --------------------------------------------------------
    # STEP 1: Retrieve RAG information
    # --------------------------------------------------------

    retrieval_result = (
        retrieve_rag_information(
            complaint=complaint,
            department=department,
            top_k=top_k,
        )
    )

    similar_complaints = (
        retrieval_result[
            "similar_complaints"
        ]
    )

    knowledge_documents = (
        retrieval_result[
            "knowledge_documents"
        ]
    )

    # --------------------------------------------------------
    # STEP 2: Build combined context
    # --------------------------------------------------------

    retrieved_context = (
        build_combined_rag_context(
            complaint=complaint,
            similar_complaints=similar_complaints,
            knowledge_documents=knowledge_documents,
        )
    )

    # --------------------------------------------------------
    # STEP 3: Build unified sources
    # --------------------------------------------------------

    sources = build_rag_sources(
        similar_complaints=similar_complaints,
        knowledge_documents=knowledge_documents,
    )

    # --------------------------------------------------------
    # STEP 4: Return structured RAG response
    # --------------------------------------------------------

    return {
        "complaint": complaint,
        "department": department,

        "similar_complaints": (
            similar_complaints
        ),

        "knowledge_documents": (
            knowledge_documents
        ),

        "retrieved_context": (
            retrieved_context
        ),

        "sources": sources,

        "model": RAG_MODEL_NAME,

        "status": "RETRIEVED",
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    predicted_department = "Plumbing"

    result = run_rag_pipeline(
        complaint=complaint,
        top_k=5,
        department=predicted_department,
    )

    print("\n" + "=" * 70)
    print("COMPLETE RAG PIPELINE")
    print("=" * 70)

    print("\nComplaint:")
    print(result["complaint"])

    print("\nDepartment:")
    print(result["department"])

    print("\nModel:")
    print(result["model"])

    print("\nSimilar Historical Complaints:")

    for item in result[
        "similar_complaints"
    ]:

        print(
            f"- ID={item['complaint_id']} | "
            f"category={item['category']} | "
            f"similarity="
            f"{item['similarity']:.4f}"
        )

    print("\nKnowledge Documents:")

    for item in result[
        "knowledge_documents"
    ]:

        print(
            f"- {item['source']} | "
            f"similarity="
            f"{item['similarity']:.4f}"
        )

    print("\nSources:")

    for source in result["sources"]:

        print(
            f"- {source['type']} | "
            f"{source['source']} | "
            f"similarity="
            f"{source['similarity']:.4f}"
        )

    print("\nRetrieved Context:")
    print(result["retrieved_context"])

    print("\nStatus:")
    print(result["status"])