from typing import List, Dict


def build_rag_context(
    complaint: str,
    retrieved_documents: List[Dict],
) -> str:
    """
    Build the context that will be provided to the AI model.

    Args:
        complaint: The original complaint.
        retrieved_documents: Documents returned by the RAG retriever.

    Returns:
        A formatted context string.
    """

    if not isinstance(complaint, str) or not complaint.strip():
        raise ValueError("complaint must be a non-empty string.")

    if not retrieved_documents:
        return (
            "COMPLAINT:\n"
            f"{complaint}\n\n"
            "RETRIEVED KNOWLEDGE:\n"
            "No relevant knowledge documents were found."
        )

    context_parts = [
        "COMPLAINT:",
        complaint.strip(),
        "",
        "RETRIEVED KNOWLEDGE:",
    ]

    for index, document in enumerate(retrieved_documents, start=1):

        source = document.get("source", "unknown")
        similarity = document.get("similarity", 0.0)
        text = document.get("text", "")

        context_parts.extend(
            [
                "",
                f"[Source {index}]",
                f"Document: {source}",
                f"Similarity: {similarity:.4f}",
                "Content:",
                text.strip(),
            ]
        )

    return "\n".join(context_parts)


if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    sample_documents = [
        {
            "source": "plumbing.txt",
            "similarity": 0.5037,
            "text": (
                "For a reported water leakage, identify "
                "the exact location and estimate whether "
                "the leakage is minor or severe."
            ),
        },
        {
            "source": "electrical.txt",
            "similarity": 0.2157,
            "text": (
                "Identify the affected building or area "
                "and determine whether the outage is "
                "isolated or widespread."
            ),
        },
    ]

    context = build_rag_context(
        complaint,
        sample_documents,
    )

    print("\n" + "=" * 60)
    print("RAG CONTEXT")
    print("=" * 60)
    print(context)