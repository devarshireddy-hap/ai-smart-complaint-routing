from typing import Dict, List


def generate_suggested_resolution(
    complaint: str,
    retrieved_documents: List[Dict],
) -> str:
    """
    Generate a prototype suggested resolution from retrieved knowledge.

    This is NOT an LLM call.
    It is a temporary prototype for demonstrating the RAG response stage.
    """

    if not isinstance(complaint, str) or not complaint.strip():
        raise ValueError("complaint must be a non-empty string.")

    if not retrieved_documents:
        return (
            "No relevant knowledge was retrieved. "
            "The complaint should be reviewed manually."
        )

    # Use the highest-ranked retrieved document.
    best_document = retrieved_documents[0]

    source = best_document.get("source", "unknown")
    text = best_document.get("text", "")

    return (
        f"Suggested resolution based on {source}: "
        f"Review the relevant procedure below and assign the complaint "
        f"to the responsible department for action.\n\n"
        f"{text}"
    )


def build_ai_response(
    complaint: str,
    retrieved_documents: List[Dict],
) -> Dict:
    """
    Build the structured AI response.
    """

    suggested_resolution = generate_suggested_resolution(
        complaint,
        retrieved_documents,
    )

    return {
        "complaint": complaint,
        "suggested_resolution": suggested_resolution,
        "sources": [
            {
                "source": document.get("source"),
                "similarity": document.get("similarity"),
            }
            for document in retrieved_documents
        ],
        "status": "PROTOTYPE",
    }


if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    documents = [
        {
            "source": "plumbing.txt",
            "similarity": 0.5037,
            "text": (
                "For a reported water leakage, identify "
                "the exact location and estimate whether "
                "the leakage is minor or severe.\n\n"
                "Severe leakage:\n"
                "Notify the plumbing maintenance team "
                "immediately and restrict the affected area "
                "if necessary."
            ),
        }
    ]

    response = build_ai_response(
        complaint,
        documents,
    )

    print("\n" + "=" * 60)
    print("AI RESPONSE")
    print("=" * 60)

    print("\nComplaint:")
    print(response["complaint"])

    print("\nSuggested Resolution:")
    print(response["suggested_resolution"])

    print("\nSources:")

    for source in response["sources"]:
        print(
            f"- {source['source']} "
            f"(similarity={source['similarity']:.4f})"
        )

    print("\nStatus:")
    print(response["status"])