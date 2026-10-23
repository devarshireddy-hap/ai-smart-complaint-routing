"""
RAG response builder.

Flow:
1. Receive retrieved RAG information.
2. Build a grounded prompt.
3. Try Gemini for AI-generated resolution.
4. If Gemini is unavailable, use a local RAG-based fallback.
5. Return the final structured response.
"""

from typing import Dict, List, Optional

from ai.config import (
    ENABLE_LLM,
    USE_LLM_FALLBACK,
)

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

# Prevent repeated API calls after a quota/rate-limit failure
LLM_AVAILABLE = True


# ============================================================
# LOCAL FALLBACK
# ============================================================

def generate_fallback_resolution(
    similar_complaints: List[Dict],
    knowledge_documents: List[Dict],
) -> str:
    """
    Generate a deterministic resolution without calling Gemini.

    Uses the strongest historical resolution and relevant
    knowledge-base guidance.
    """

    response_parts = []

    # --------------------------------------------------------
    # Historical resolution
    # --------------------------------------------------------

    if similar_complaints:

        best_complaint = similar_complaints[0]

        resolution = best_complaint.get(
            "resolution",
            "",
        )

        complaint_id = best_complaint.get(
            "complaint_id",
            "unknown",
        )

        similarity = float(
            best_complaint.get(
                "similarity",
                0.0,
            )
        )

        if resolution:

            response_parts.append(
                "Recommended approach based on "
                f"historical complaint ID={complaint_id} "
                f"(similarity={similarity:.4f}):\n"
                f"{resolution}"
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

        text = best_document.get(
            "text",
            "",
        )

        if text:

            response_parts.append(
                f"Relevant knowledge-base guidance "
                f"from {source}:\n"
                f"{text}"
            )

    # --------------------------------------------------------
    # Nothing available
    # --------------------------------------------------------

    if not response_parts:

        return (
            "No relevant RAG information was available. "
            "The complaint should be reviewed manually."
        )

    return "\n\n".join(response_parts)


# ============================================================
# SUGGESTED RESOLUTION
# ============================================================

def generate_suggested_resolution(
    complaint: str,
    department: str,
    category: str,
    priority: str,
    retrieved_context: str,
    similar_complaints: List[Dict],
    knowledge_documents: List[Dict],
) -> str:
    """
    Generate the complaint resolution.

    Gemini is used when enabled and available.

    If Gemini fails and fallback is enabled, a local
    RAG-based resolution is returned instead.
    """

    global LLM_AVAILABLE

    if not isinstance(
        complaint,
        str,
    ) or not complaint.strip():

        raise ValueError(
            "complaint must be a non-empty string."
        )

    # --------------------------------------------------------
    # Try Gemini
    # --------------------------------------------------------

    if ENABLE_LLM and LLM_AVAILABLE:

        try:

            prompt = build_resolution_prompt(
                complaint=complaint,
                department=department,
                category=category,
                priority=priority,
                retrieved_context=retrieved_context,
            )

            return generate_resolution(prompt)

        except Exception as error:

            print(
                "\nWarning: Gemini generation failed."
            )

            print(
                f"Reason: {error}"
            )

            # Stop repeated API requests for this process
            LLM_AVAILABLE = False

            if not USE_LLM_FALLBACK:
                raise

    # --------------------------------------------------------
    # Local fallback
    # --------------------------------------------------------

    return generate_fallback_resolution(
        similar_complaints=similar_complaints,
        knowledge_documents=knowledge_documents,
    )


# ============================================================
# STRUCTURED RESPONSE
# ============================================================

def build_ai_response(
    complaint: str,
    department: str,
    category: str,
    priority: str,
    retrieved_context: str,
    similar_complaints: Optional[List[Dict]] = None,
    knowledge_documents: Optional[List[Dict]] = None,
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

    suggested_resolution = (
        generate_suggested_resolution(
            complaint=complaint,
            department=department,
            category=category,
            priority=priority,
            retrieved_context=retrieved_context,
            similar_complaints=similar_complaints,
            knowledge_documents=knowledge_documents,
        )
    )

    # Tell the caller whether Gemini or fallback produced it
    response_model = (
        RAG_MODEL_NAME
        if LLM_AVAILABLE and ENABLE_LLM
        else "RAG-Fallback"
    )

    response_status = (
        "GENERATED"
        if LLM_AVAILABLE and ENABLE_LLM
        else "GENERATED_WITH_FALLBACK"
    )

    return {
        "complaint": complaint,

        "department": department,

        "category": category,

        "priority": priority,

        "retrieved_context": retrieved_context,

        "similar_complaints": similar_complaints,

        "knowledge_documents": knowledge_documents,

        "suggested_resolution": (
            suggested_resolution
        ),

        "sources": sources,

        "model": response_model,

        "status": response_status,
    }