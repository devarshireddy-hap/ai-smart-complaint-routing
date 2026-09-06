"""
RAG response builder.

This module:
1. Receives retrieved RAG information.
2. Builds a grounded prompt.
3. Sends the prompt to Gemini.
4. Returns the generated resolution together with
   the retrieved evidence.

The Gemini API key is loaded from .env.
"""

from typing import Dict, List, Optional

from ai.prompts.resolution_prompt import (
    build_resolution_prompt,
)

from ai.llm.gemini_client import (
    generate_resolution,
)


# ============================================================
# MODEL
# ============================================================

RAG_MODEL_NAME = "gemini-3.8-flash"


# ============================================================
# AI RESPONSE
# ============================================================

def generate_suggested_resolution(
    complaint: str,
    department: str,
    category: str,
    priority: str,
    retrieved_context: str,
) -> str:
    """
    Generate a suggested resolution using Gemini.

    The Gemini prompt is grounded in the retrieved RAG context.
    """

    if not isinstance(
        complaint,
        str,
    ) or not complaint.strip():
        raise ValueError(
            "complaint must be a non-empty string."
        )

    prompt = build_resolution_prompt(
        complaint=complaint,
        department=department,
        category=category,
        priority=priority,
        retrieved_context=retrieved_context,
    )

    return generate_resolution(prompt)


# ============================================================
# STRUCTURED RESPONSE
# ============================================================

def build_ai_response(
    complaint: str,
    department: str,
    category: str,
    priority: str,
    retrieved_context: str,
    similar_complaints: Optional[
        List[Dict]
    ] = None,
    knowledge_documents: Optional[
        List[Dict]
    ] = None,
    sources: Optional[List[Dict]] = None,
) -> Dict:
    """
    Build the final structured AI response.
    """

    if not isinstance(
        complaint,
        str,
    ) or not complaint.strip():
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

    # --------------------------------------------------------
    # Generate Gemini response
    # --------------------------------------------------------

    suggested_resolution = (
        generate_suggested_resolution(
            complaint=complaint,
            department=department,
            category=category,
            priority=priority,
            retrieved_context=retrieved_context,
        )
    )

    return {
        "complaint": complaint,

        "department": department,

        "category": category,

        "priority": priority,

        "retrieved_context": (
            retrieved_context
        ),

        "similar_complaints": (
            similar_complaints
        ),

        "knowledge_documents": (
            knowledge_documents
        ),

        "suggested_resolution": (
            suggested_resolution
        ),

        "sources": sources,

        "model": RAG_MODEL_NAME,

        "status": "GENERATED",
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    department = "Plumbing"
    category = "Water Leakage"
    priority = "HIGH"

    retrieved_context = """
CURRENT COMPLAINT
There is a serious water pipe leak behind the hostel building.

SIMILAR HISTORICAL COMPLAINT
Complaint ID: 40
Complaint: The plumbing pipe behind the hostel building is leaking
Resolution: Inspect the affected pipeline and repair the leak.

KNOWLEDGE BASE
Severe leakage:
Notify the plumbing maintenance team immediately
and restrict the affected area if necessary.
""".strip()

    response = build_ai_response(
        complaint=complaint,
        department=department,
        category=category,
        priority=priority,
        retrieved_context=retrieved_context,
        similar_complaints=[
            {
                "complaint_id": 40,
                "similarity": 0.8765,
                "category": "Water Leakage",
                "priority": "HIGH",
                "resolution": (
                    "Inspect the affected pipeline "
                    "and repair the leak."
                ),
            }
        ],
        knowledge_documents=[
            {
                "source": "plumbing.txt",
                "similarity": 0.5037,
            }
        ],
        sources=[
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
        ],
    )

    print("\n" + "=" * 70)
    print("GEMINI RAG RESPONSE")
    print("=" * 70)

    print("\nComplaint:")
    print(response["complaint"])

    print("\nDepartment:")
    print(response["department"])

    print("\nCategory:")
    print(response["category"])

    print("\nPriority:")
    print(response["priority"])

    print("\nModel:")
    print(response["model"])

    print("\nAI-Generated Suggested Resolution:")
    print(response["suggested_resolution"])

    print("\nStatus:")
    print(response["status"])