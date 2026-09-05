"""
RAG pipeline.

Pipeline:
Complaint
    -> Department-aware retrieval
    -> Context building
    -> AI-ready context
"""

from typing import Dict, List, Optional

from ai.rag.retriever import retrieve_relevant_documents
from ai.rag.context_builder import build_rag_context


def run_rag_pipeline(
    complaint: str,
    top_k: int = 3,
    department: Optional[str] = None,
) -> Dict:
    """
    Run the RAG retrieval pipeline.

    Args:
        complaint:
            New complaint text.

        top_k:
            Number of knowledge documents to retrieve.

        department:
            Predicted complaint department.
            If supplied, retrieval is restricted to that department.

    Returns:
        Dictionary containing:
        - complaint
        - department
        - retrieved_documents
        - context
    """

    if not isinstance(complaint, str):
        raise ValueError(
            "complaint must be a string."
        )

    if not complaint.strip():
        raise ValueError(
            "complaint must be a non-empty string."
        )

    # -----------------------------------------
    # STEP 1: Retrieve relevant knowledge
    # -----------------------------------------

    retrieved_documents = (
        retrieve_relevant_documents(
            complaint=complaint,
            top_k=top_k,
            department=department,
        )
    )

    # -----------------------------------------
    # STEP 2: Build AI context
    # -----------------------------------------

    context = build_rag_context(
        complaint=complaint,
        retrieved_documents=retrieved_documents,
    )

    return {
        "complaint": complaint,
        "department": department,
        "retrieved_documents": retrieved_documents,
        "context": context,
    }


if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    predicted_department = "Plumbing"

    result = run_rag_pipeline(
        complaint=complaint,
        top_k=3,
        department=predicted_department,
    )

    print("\n" + "=" * 60)
    print("RAG PIPELINE")
    print("=" * 60)

    print("\nComplaint:")
    print(result["complaint"])

    print(
        "\nDepartment:"
    )
    print(result["department"])

    print("\nRetrieved Sources:")

    for document in result[
        "retrieved_documents"
    ]:

        print(
            f"- {document['source']} "
            f"(similarity="
            f"{document['similarity']:.4f})"
        )

    print("\nRAG Context:")
    print(result["context"])