"""
RAG response builder.

This module converts retrieved RAG information into a structured
AI-ready response.

Current implementation:
- Uses historical complaint resolutions when available.
- Uses knowledge-base guidance.
- Does NOT call an external LLM yet.

The LLM integration can be added later without changing the
retrieval pipeline.
"""

from typing import Dict, List, Optional


RAG_MODEL_NAME = "all-MiniLM-L6-v2"


# ============================================================
# SUGGESTED RESOLUTION
# ============================================================

def generate_suggested_resolution(
    complaint: str,
    similar_complaints: List[Dict],
    knowledge_documents: List[Dict],
) -> str:
    """
    Generate a prototype suggested resolution.

    Historical complaint resolutions are used as the primary
    practical reference. Knowledge-base content provides
    additional department-specific guidance.

    This is NOT an LLM call.
    """

    if not isinstance(complaint, str) or not complaint.strip():
        raise ValueError(
            "complaint must be a non-empty string."
        )

    # --------------------------------------------------------
    # No retrieved information
    # --------------------------------------------------------

    if not similar_complaints and not knowledge_documents:
        return (
            "No relevant information was retrieved. "
            "The complaint should be reviewed manually."
        )

    response_parts = []

    # --------------------------------------------------------
    # Historical resolution
    # --------------------------------------------------------

    if similar_complaints:

        best_complaint = similar_complaints[0]

        historical_resolution = (
            best_complaint.get("resolution", "")
        )

        complaint_id = (
            best_complaint.get("complaint_id", "unknown")
        )

        similarity = float(
            best_complaint.get("similarity", 0.0)
        )

        if historical_resolution:
            response_parts.append(
                "Recommended approach based on the "
                f"most similar historical complaint "
                f"(ID={complaint_id}, "
                f"similarity={similarity:.4f}):\n"
                f"{historical_resolution}"
            )

    # --------------------------------------------------------
    # Knowledge-base guidance
    # --------------------------------------------------------

    if knowledge_documents:

        best_document = knowledge_documents[0]

        source = best_document.get(
            "source",
            "knowledge base",
        )

        knowledge_text = best_document.get(
            "text",
            "",
        )

        if knowledge_text:

            response_parts.append(
                "Relevant knowledge-base guidance "
                f"from {source}:\n"
                f"{knowledge_text}"
            )

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    if not response_parts:
        return (
            "Relevant information was retrieved, but "
            "no usable resolution text was available. "
            "The complaint should be reviewed manually."
        )

    return "\n\n".join(response_parts)


# ============================================================
# STRUCTURED AI RESPONSE
# ============================================================

def build_ai_response(
    complaint: str,
    similar_complaints: Optional[List[Dict]] = None,
    knowledge_documents: Optional[List[Dict]] = None,
    retrieved_context: str = "",
    sources: Optional[List[Dict]] = None,
) -> Dict:
    """
    Build the structured AI response.

    This response structure is designed for later integration
    with an actual LLM.
    """

    if not isinstance(complaint, str) or not complaint.strip():
        raise ValueError(
            "complaint must be a non-empty string."
        )

    similar_complaints = (
        similar_complaints
        if similar_complaints is not None
        else []
    )

    knowledge_documents = (
        knowledge_documents
        if knowledge_documents is not None
        else []
    )

    sources = (
        sources
        if sources is not None
        else []
    )

    suggested_resolution = (
        generate_suggested_resolution(
            complaint=complaint,
            similar_complaints=similar_complaints,
            knowledge_documents=knowledge_documents,
        )
    )

    return {
        "complaint": complaint,

        "retrieved_context": retrieved_context,

        "similar_complaints": similar_complaints,

        "knowledge_documents": knowledge_documents,

        "suggested_resolution": (
            suggested_resolution
        ),

        "sources": sources,

        "model": RAG_MODEL_NAME,

        "status": "PROTOTYPE",
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    similar_complaints = [
        {
            "complaint_id": 40,
            "complaint_text": (
                "The plumbing pipe behind the "
                "hostel building is leaking"
            ),
            "department": "Plumbing",
            "category": "Water Leakage",
            "priority": "HIGH",
            "similarity": 0.8765,
            "resolution": (
                "Inspect the affected pipeline "
                "and repair the leak."
            ),
        }
    ]

    knowledge_documents = [
        {
            "source": "plumbing.txt",
            "department": "Plumbing",
            "similarity": 0.5037,
            "text": (
                "Water Leakage:\n"
                "For a reported water leakage, identify "
                "the exact location and estimate whether "
                "the leakage is minor or severe.\n\n"
                "Severe leakage:\n"
                "Notify the plumbing maintenance team "
                "immediately and restrict the affected "
                "area if necessary."
            ),
        }
    ]

    sources = [
        {
            "type": "historical_complaint",
            "source": "complaint_40",
            "similarity": 0.8765,
        },
        {
            "type": "knowledge_document",
            "source": "plumbing.txt",
            "similarity": 0.5037,
        },
    ]

    response = build_ai_response(
        complaint=complaint,
        similar_complaints=similar_complaints,
        knowledge_documents=knowledge_documents,
        retrieved_context=(
            "CURRENT COMPLAINT\n"
            "There is a serious water pipe leak "
            "behind the hostel building."
        ),
        sources=sources,
    )

    print("\n" + "=" * 70)
    print("AI RESPONSE")
    print("=" * 70)

    print("\nComplaint:")
    print(response["complaint"])

    print("\nModel:")
    print(response["model"])

    print("\nSuggested Resolution:")
    print(response["suggested_resolution"])

    print("\nHistorical Complaints:")

    for item in response["similar_complaints"]:
        print(
            f"- ID={item['complaint_id']} | "
            f"similarity={item['similarity']:.4f}"
        )

    print("\nKnowledge Documents:")

    for item in response["knowledge_documents"]:
        print(
            f"- {item['source']} | "
            f"similarity={item['similarity']:.4f}"
        )

    print("\nSources:")

    for source in response["sources"]:
        print(
            f"- {source['type']} | "
            f"{source['source']} | "
            f"similarity="
            f"{source['similarity']:.4f}"
        )

    print("\nStatus:")
    print(response["status"])