"""
Prompt builder for AI-generated complaint resolution.

This module prepares the RAG context for an LLM.

No external API is called here yet.
"""

from typing import Dict


def build_resolution_prompt(
    complaint: str,
    department: str,
    category: str,
    priority: str,
    retrieved_context: str,
) -> str:
    """
    Build the prompt that will later be sent to an LLM.
    """

    if not complaint.strip():
        raise ValueError(
            "complaint must be a non-empty string."
        )

    prompt = f"""
You are an AI assistant for a college complaint
routing and resolution system.

Your task is to suggest a practical resolution for the
complaint using ONLY the retrieved project information.

Complaint:
{complaint}

Predicted Department:
{department}

Predicted Category:
{category}

Predicted Priority:
{priority}

Retrieved Project Context:
{retrieved_context}

Instructions:
1. Use the retrieved historical complaints and their
   resolutions as supporting examples.
2. Use the knowledge-base information as procedural guidance.
3. Do not invent facts that are not supported by the context.
4. Give a concise, actionable suggested resolution.
5. Mention escalation when the retrieved information
   indicates that escalation is necessary.
6. Do not change the predicted department, category,
   or priority.

Return only the suggested resolution.
""".strip()

    return prompt


if __name__ == "__main__":

    complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    context = """
SIMILAR HISTORICAL COMPLAINT:
Complaint ID: 40
Complaint: The plumbing pipe behind the hostel building is leaking
Resolution: Inspect the affected pipeline and repair the leak.

KNOWLEDGE BASE:
Severe leakage:
Notify the plumbing maintenance team immediately
and restrict the affected area if necessary.
"""

    prompt = build_resolution_prompt(
        complaint=complaint,
        department="Plumbing",
        category="Water Leakage",
        priority="HIGH",
        retrieved_context=context,
    )

    print("=" * 70)
    print("LLM RESOLUTION PROMPT")
    print("=" * 70)
    print(prompt)
    