import csv
import logging
import os
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import requests

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "complaints.csv"
KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "knowledge_base"
DEPARTMENTS = ("Technical", "Finance", "Electrical", "Plumbing", "Security")
SIMILARITY_THRESHOLD = 0.78


@lru_cache(maxsize=1)
def _load_examples():
    with DATASET_PATH.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    required = {"complaint_text", "department", "category", "priority", "resolution"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"AI training data must contain columns: {sorted(required)}")
    return rows


@lru_cache(maxsize=1)
def _load_knowledge():
    result = []
    for department in DEPARTMENTS:
        path = KNOWLEDGE_PATH / f"{department.lower()}.txt"
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                result.append({"department": department, "source": path.name, "text": text})
    return result


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def _lexical_similarity(left, right):
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@lru_cache(maxsize=1)
def _semantic_model():
    try:
        from ai.embeddings.embedding_model import load_embedding_model

        return load_embedding_model(), None
    except (ImportError, OSError, RuntimeError, requests.exceptions.RequestException) as error:
        logger.warning("Sentence Transformer unavailable; using example-based local matching: %s", error)
        return None, "Sentence Transformer unavailable; local example-matching mode is active."


def _similarities(text, candidates):
    model, fallback_reason = _semantic_model()
    if model is not None:
        query_vector = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        candidate_vectors = model.encode(
            candidates,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return [float(score) for score in candidate_vectors @ query_vector], "sentence-transformers", None
    return [_lexical_similarity(text, candidate) for candidate in candidates], "example-matcher", fallback_reason


def generate_embedding(text):
    vectors = generate_embeddings([text])
    return vectors[0] if vectors else None


def generate_embeddings(texts):
    if not texts:
        return []
    model, _ = _semantic_model()
    if model is None:
        return []
    vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return [[float(value) for value in vector] for vector in vectors]


def generate_external_resolution(text, result):
    if os.getenv("ENABLE_GEMINI", "false").lower() != "true":
        raise ValueError("External AI generation is not enabled by the server.")
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is required when external AI generation is enabled.")

    import httpx
    from google.genai import errors
    from ai.llm.gemini_client import generate_resolution

    prompt = (
        "Suggest a concise, safe next step for this campus complaint. "
        "Use only the supplied routing and retrieved context. Do not claim work has already been done. "
        "The suggestion is advisory and must be reviewed by staff.\n\n"
        f"Complaint: {text}\n"
        f"Department: {result['department']}\n"
        f"Category: {result['category']}\n"
        f"Priority: {result['priority']}\n"
        f"Retrieved context: {result['suggested_resolution']}"
    )
    try:
        return generate_resolution(prompt), None
    except (errors.APIError, httpx.RequestError) as error:
        logger.warning("Gemini request failed; retaining local suggestion: %s", error)
        return None, "Gemini is unavailable; the local suggestion was retained."


def analyze_complaint(text, department_override=None):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Complaint text must not be empty.")

    examples = _load_examples()
    scores, model_name, model_warning = _similarities(
        text.strip(),
        [row["complaint_text"] for row in examples],
    )
    ranked = sorted(
        ({"row": row, "score": score} for row, score in zip(examples, scores)),
        key=lambda item: item["score"],
        reverse=True,
    )
    nearest = ranked[:5]

    department_scores = defaultdict(float)
    category_votes = Counter()
    priority_votes = Counter()
    for item in nearest:
        row = item["row"]
        department_scores[row["department"]] += item["score"]
        category_votes[row["category"]] += item["score"]
        priority_votes[row["priority"]] += item["score"]

    department = max(department_scores, key=department_scores.get)
    if department_override:
        normalized_override = str(department_override).strip().casefold()
        known_department = next(
            (name for name in DEPARTMENTS if name.casefold() == normalized_override),
            None,
        )
        if known_department is None:
            raise ValueError("department_override must be one of the supported departments.")
        department = known_department
    department_rows = [
        item for item in ranked
        if item["row"]["department"].casefold() == department.casefold()
    ][:5]
    category_scores = Counter()
    for item in department_rows:
        category_scores[item["row"]["category"]] += item["score"]
    category = max(category_scores, key=category_scores.get)
    priority = max(priority_votes, key=priority_votes.get)
    department_nearest = department_rows or nearest
    best_match = department_nearest[0]

    documents = [doc for doc in _load_knowledge() if doc["department"].casefold() == department.casefold()]
    knowledge_scores, _, _ = _similarities(text.strip(), [doc["text"] for doc in documents]) if documents else ([], model_name, None)
    knowledge = sorted(
        ({"source": doc["source"], "department": doc["department"], "text": doc["text"], "similarity": score}
         for doc, score in zip(documents, knowledge_scores)),
        key=lambda item: item["similarity"],
        reverse=True,
    )

    resolution_parts = []
    if best_match["row"].get("resolution"):
        resolution_parts.append(f"Suggested from a similar historical case: {best_match['row']['resolution']}")
    if knowledge:
        first_line = next((line.strip() for line in knowledge[0]["text"].splitlines() if line.strip()), "")
        if first_line:
            resolution_parts.append(f"Department guidance ({knowledge[0]['source']}): {first_line}")
    suggested_resolution = " ".join(resolution_parts) or "Please have the assigned department review this complaint."
    similar = [
        {
            "complaint_text": item["row"]["complaint_text"],
            "department": item["row"]["department"],
            "category": item["row"]["category"],
            "resolution": item["row"]["resolution"],
            "similarity": round(item["score"], 4),
        }
        for item in department_nearest
    ]
    return {
        "department": department.upper(),
        "category": category,
        "priority": priority.upper(),
        "duplicate": bool(nearest and nearest[0]["score"] >= SIMILARITY_THRESHOLD),
        "similar_complaints": similar,
        "knowledge_documents": [
            {"source": item["source"], "similarity": round(item["similarity"], 4)}
            for item in knowledge
        ],
        "suggested_resolution": suggested_resolution,
        "model": model_name,
        "warning": model_warning,
    }
