"""
RAG retriever.

Retrieves three types of project-specific information:

1. Similar historical complaints
2. Historical complaint resolutions
3. Department-specific knowledge-base documents

Semantic similarity is used. No keyword matching.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd

from ai.embeddings.embedding_generator import generate_embedding


# ============================================================
# CONFIGURATION
# ============================================================

TOP_K = 5

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "complaints.csv"
)

KNOWLEDGE_BASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "knowledge_base"
)


# ============================================================
# DATASET
# ============================================================

def load_historical_complaints() -> pd.DataFrame:
    """
    Load historical complaints from the project dataset.
    """

    df = pd.read_csv(DATA_PATH)

    required_columns = [
        "complaint_id",
        "complaint_text",
        "department",
        "category",
        "priority",
        "resolution",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    return df


# ============================================================
# KNOWLEDGE BASE
# ============================================================

def load_knowledge_documents(
    department: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Load department-specific knowledge-base documents.
    """

    documents = []

    if department:
        departments = [department]
    else:
        departments = [
            "Technical",
            "Finance",
            "Electrical",
            "Plumbing",
            "Security",
        ]

    for department_name in departments:

        file_path = (
            KNOWLEDGE_BASE_PATH
            / f"{department_name.lower()}.txt"
        )

        if not file_path.exists():
            continue

        text = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            continue

        documents.append(
            {
                "source": file_path.name,
                "department": department_name,
                "text": text,
            }
        )

    return documents


# ============================================================
# HISTORICAL COMPLAINT RETRIEVAL
# ============================================================

def retrieve_similar_complaints(
    complaint: str,
    department: Optional[str] = None,
    top_k: int = TOP_K,
) -> List[Dict[str, Any]]:
    """
    Retrieve semantically similar historical complaints.

    When a department is supplied, only complaints from
    that department are considered.
    """

    df = load_historical_complaints()

    if department:
        df = df[
            df["department"].str.upper()
            == department.upper()
        ]

    if df.empty:
        return []

    texts = (
        df["complaint_text"]
        .astype(str)
        .tolist()
    )

    historical_embeddings = np.array(
        [
            generate_embedding(text)
            for text in texts
        ]
    )

    query_embedding = np.array(
        generate_embedding(complaint)
    )

    similarities = (
        historical_embeddings @ query_embedding
    )

    top_k = min(top_k, len(df))

    top_indices = np.argsort(
        similarities
    )[-top_k:][::-1]

    results = []

    for index in top_indices:

        row = df.iloc[index]

        results.append(
            {
                "complaint_id": int(
                    row["complaint_id"]
                ),
                "complaint_text": str(
                    row["complaint_text"]
                ),
                "department": str(
                    row["department"]
                ),
                "category": str(
                    row["category"]
                ),
                "priority": str(
                    row["priority"]
                ),
                "resolution": str(
                    row["resolution"]
                ),
                "similarity": float(
                    similarities[index]
                ),
            }
        )

    return results


# ============================================================
# KNOWLEDGE DOCUMENT RETRIEVAL
# ============================================================

def retrieve_knowledge_documents(
    complaint: str,
    department: Optional[str] = None,
    top_k: int = TOP_K,
) -> List[Dict[str, Any]]:
    """
    Retrieve department-specific knowledge documents
    using semantic similarity.
    """

    documents = load_knowledge_documents(
        department=department
    )

    if not documents:
        return []

    query_embedding = np.array(
        generate_embedding(complaint)
    )

    document_results = []

    for document in documents:

        document_embedding = np.array(
            generate_embedding(
                document["text"]
            )
        )

        similarity = float(
            document_embedding
            @ query_embedding
        )

        document_results.append(
            {
                "source": document["source"],
                "department": document["department"],
                "text": document["text"],
                "similarity": similarity,
            }
        )

    document_results.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    return document_results[:top_k]


# ============================================================
# COMPLETE RAG RETRIEVAL
# ============================================================

def retrieve_rag_information(
    complaint: str,
    department: Optional[str] = None,
    top_k: int = TOP_K,
) -> Dict[str, Any]:
    """
    Retrieve all project-specific RAG information.
    """

    similar_complaints = (
        retrieve_similar_complaints(
            complaint=complaint,
            department=department,
            top_k=top_k,
        )
    )

    knowledge_documents = (
        retrieve_knowledge_documents(
            complaint=complaint,
            department=department,
            top_k=top_k,
        )
    )

    return {
        "similar_complaints": similar_complaints,
        "knowledge_documents": knowledge_documents,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    print("=" * 70)
    print("RAG RETRIEVAL TEST")
    print("=" * 70)

    result = retrieve_rag_information(
        complaint=complaint,
        department="Plumbing",
        top_k=5,
    )

    print("\nSIMILAR HISTORICAL COMPLAINTS")

    for item in result[
        "similar_complaints"
    ]:

        print(
            f"\nID: {item['complaint_id']}"
        )

        print(
            f"Complaint: "
            f"{item['complaint_text']}"
        )

        print(
            f"Category: "
            f"{item['category']}"
        )

        print(
            f"Priority: "
            f"{item['priority']}"
        )

        print(
            f"Similarity: "
            f"{item['similarity']:.4f}"
        )

        print(
            f"Resolution: "
            f"{item['resolution']}"
        )

    print("\nKNOWLEDGE DOCUMENTS")

    for document in result[
        "knowledge_documents"
    ]:

        print(
            f"\nSource: "
            f"{document['source']}"
        )

        print(
            f"Similarity: "
            f"{document['similarity']:.4f}"
        )

        print(
            document["text"]
        )