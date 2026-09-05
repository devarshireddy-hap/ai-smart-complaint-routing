from pathlib import Path
from typing import List, Dict, Optional

import numpy as np

from ai.embeddings.embedding_model import load_embedding_model


TOP_K = 3

KNOWLEDGE_BASE_DIR = Path("data/knowledge_base")


def cosine_similarity(vector_a, vector_b) -> float:
    """Calculate cosine similarity between two vectors."""

    a = np.asarray(vector_a, dtype=float)
    b = np.asarray(vector_b, dtype=float)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)


def load_documents(
    department: Optional[str] = None,
) -> List[Dict]:
    """
    Load knowledge-base documents.

    If a department is supplied, only that department's
    knowledge document is loaded.
    """

    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            f"Knowledge base not found: {KNOWLEDGE_BASE_DIR}"
        )

    documents = []

    if department:
        department_file = (
            KNOWLEDGE_BASE_DIR
            / f"{department.lower()}.txt"
        )

        if not department_file.exists():
            raise FileNotFoundError(
                f"Knowledge document not found for "
                f"department '{department}': "
                f"{department_file}"
            )

        text = department_file.read_text(
            encoding="utf-8"
        ).strip()

        if text:
            documents.append(
                {
                    "source": department_file.name,
                    "department": department,
                    "text": text,
                }
            )

    else:
        for file_path in KNOWLEDGE_BASE_DIR.glob("*.txt"):

            text = file_path.read_text(
                encoding="utf-8"
            ).strip()

            if text:
                documents.append(
                    {
                        "source": file_path.name,
                        "department": file_path.stem.title(),
                        "text": text,
                    }
                )

    if not documents:
        raise ValueError(
            "No knowledge-base documents were found."
        )

    return documents


def retrieve_relevant_documents(
    complaint: str,
    top_k: int = TOP_K,
    department: Optional[str] = None,
) -> List[Dict]:
    """
    Retrieve the most semantically relevant knowledge documents.

    Args:
        complaint:
            New complaint text.

        top_k:
            Number of documents to return.

        department:
            Optional predicted department. If supplied,
            retrieval is restricted to that department.

    Returns:
        Ranked list of relevant documents.
    """

    if not isinstance(complaint, str):
        raise ValueError(
            "complaint must be a string."
        )

    if not complaint.strip():
        raise ValueError(
            "complaint must be a non-empty string."
        )

    documents = load_documents(
        department=department
    )

    model = load_embedding_model()

    # Embed the complaint
    complaint_embedding = model.encode(
        complaint,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    # Embed knowledge documents
    document_texts = [
        document["text"]
        for document in documents
    ]

    document_embeddings = model.encode(
        document_texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    results = []

    for index, document in enumerate(documents):

        similarity = cosine_similarity(
            complaint_embedding,
            document_embeddings[index],
        )

        results.append(
            {
                "source": document["source"],
                "department": document["department"],
                "similarity": similarity,
                "text": document["text"],
            }
        )

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    return results[:top_k]


if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    predicted_department = "Plumbing"

    print("\nNew complaint:")
    print(complaint)

    print(
        f"\nPredicted department: "
        f"{predicted_department}"
    )

    results = retrieve_relevant_documents(
        complaint=complaint,
        department=predicted_department,
    )

    print("\nRetrieved RAG documents:")

    for result in results:

        print("\n------------------------------")
        print(
            f"Source: {result['source']}"
        )
        print(
            f"Department: {result['department']}"
        )
        print(
            f"Similarity: "
            f"{result['similarity']:.4f}"
        )
        print("------------------------------")
        print(result["text"])