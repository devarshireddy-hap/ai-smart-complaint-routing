"""
Gemini LLM client.

This module sends the RAG-grounded prompt to Gemini
and returns the generated complaint resolution.
"""

import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not set. "
        "Add it to your .env file."
    )


client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.8-flash"


def generate_resolution(prompt: str) -> str:
    """
    Generate a complaint resolution using Gemini.
    """

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(
            "prompt must be a non-empty string."
        )

    response = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
    )

    return response.output_text.strip()


if __name__ == "__main__":

    test_prompt = """
Suggest a concise resolution for this complaint:

There is a serious water pipe leak behind the hostel building.

Use this information:
- Similar historical complaint: inspect the affected pipeline and repair the leak.
- Severe leakage should be escalated to the plumbing maintenance team.

Return only the suggested resolution.
""".strip()

    result = generate_resolution(test_prompt)

    print("=" * 60)
    print("GEMINI TEST")
    print("=" * 60)
    print(result)