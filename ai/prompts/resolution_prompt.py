"""
Prompt builder for AI-generated complaint resolution.

The prompt template is stored in resolution_prompt.txt.

This module loads the template and fills in the dynamic
complaint, prediction, and RAG context values.
"""

from pathlib import Path


PROMPT_FILE = (
    Path(__file__).resolve().parent
    / "resolution_prompt.txt"
)


def load_resolution_prompt_template() -> str:
    """Load the resolution prompt template from the text file."""

    if not PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {PROMPT_FILE}"
        )

    return PROMPT_FILE.read_text(
        encoding="utf-8"
    ).strip()


def build_resolution_prompt(
    complaint: str,
    department: str,
    category: str,
    priority: str,
    retrieved_context: str,
) -> str:
    """
    Build the final prompt using the documented
    resolution_prompt.txt template.
    """

    if not isinstance(
        complaint,
        str,
    ) or not complaint.strip():

        raise ValueError(
            "complaint must be a non-empty string."
        )

    template = load_resolution_prompt_template()

    return template.format(
        complaint=complaint,
        department=department,
        category=category,
        priority=priority,
        retrieved_context=retrieved_context,
    )


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
""".strip()

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