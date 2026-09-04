from typing import Dict, Any

from ai.rag.rag_pipeline import run_rag_pipeline
from ai.rag.rag_response import build_ai_response


def build_complete_ai_response(
    complaint: str,
    department: str,
    priority: str,
    is_duplicate: bool,
) -> Dict[str, Any]:
    """
    Combine routing, duplicate detection, and RAG results
    into one structured AI response.
    """

    rag_result = run_rag_pipeline(
        complaint=complaint,
        top_k=3,
    )

    rag_response = build_ai_response(
        complaint=complaint,
        retrieved_documents=rag_result["retrieved_documents"],
    )

    return {
        "complaint": complaint,
        "prediction": {
            "department": department,
            "priority": priority,
        },
        "duplicate_detection": {
            "is_duplicate": is_duplicate,
        },
        "rag": {
            "sources": rag_response["sources"],
            "suggested_resolution": rag_response[
                "suggested_resolution"
            ],
        },
        "status": "PREDICTED",
    }


if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    response = build_complete_ai_response(
        complaint=complaint,
        department="Plumbing",
        priority="HIGH",
        is_duplicate=False,
    )

    print("\n" + "=" * 60)
    print("COMPLETE AI RESPONSE")
    print("=" * 60)

    print("\nComplaint:")
    print(response["complaint"])

    print("\nPrediction:")
    print(response["prediction"])

    print("\nDuplicate Detection:")
    print(response["duplicate_detection"])

    print("\nRAG:")
    print(response["rag"])

    print("\nStatus:")
    print(response["status"])