import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


@lru_cache(maxsize=4)
def _client(api_key):
    return genai.Client(api_key=api_key)


def generate_resolution(prompt: str) -> str:
    """
    Generate a complaint resolution using Gemini.
    """

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(
            "prompt must be a non-empty string."
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is required when Gemini generation is enabled.")
    response = _client(api_key).models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty resolution suggestion.")
    return text


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