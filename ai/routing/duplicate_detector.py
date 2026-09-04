from pathlib import Path
from typing import List, Dict

import pandas as pd
import numpy as np

from ai.embeddings.embedding_model import load_embedding_model


DUPLICATE_SIMILARITY_THRESHOLD = 0.75
TOP_K = 5


def cosine_similarity(vector_a, vector_b) -> float:
    """Calculate cosine similarity between two vectors."""

    a = np.array(vector_a, dtype=float)
    b = np.array(vector_b, dtype=float)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)


def find_similar_complaints(
    new_complaint: str,
    csv_path: str = "data/complaints.csv",
    top_k: int = TOP_K,
    threshold: float = DUPLICATE_SIMILARITY_THRESHOLD,
) -> Dict:

    if not isinstance(new_complaint, str) or not new_complaint.strip():
        raise ValueError("new_complaint must be a non-empty string.")

    csv_file = Path(csv_path)

    if not csv_file.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_file}")

    df = pd.read_csv(csv_file)

    required_columns = {"complaint_id", "complaint_text"}

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Dataset is missing required columns: {missing_columns}"
        )

    # Load model only ONCE
    model = load_embedding_model()

    # Generate embedding for the new complaint
    new_embedding = model.encode(
        new_complaint,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    results = []

    # Generate embeddings for existing complaints
    existing_embeddings = model.encode(
        df["complaint_text"].astype(str).tolist(),
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    for index, row in df.iterrows():

        similarity = cosine_similarity(
            new_embedding,
            existing_embeddings[index]
        )

        results.append(
            {
                "complaint_id": int(row["complaint_id"]),
                "complaint_text": str(row["complaint_text"]),
                "department": row.get("department", "UNKNOWN"),
                "similarity": similarity,
            }
        )

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    top_matches = results[:top_k]

    is_duplicate = (
        bool(top_matches)
        and top_matches[0]["similarity"] >= threshold
    )

    return {
        "is_duplicate": is_duplicate,
        "top_matches": top_matches,
    }


if __name__ == "__main__":

    complaint = "There is a pipeline leak beside the hostel."

    result = find_similar_complaints(complaint)

    print("\nNew complaint:")
    print(complaint)

    print("\nDuplicate detected:", result["is_duplicate"])

    print("\nTop similar complaints:")

    for match in result["top_matches"]:

        print(
            f"\nComplaint ID: {match['complaint_id']}"
            f"\nDepartment: {match['department']}"
            f"\nSimilarity: {match['similarity']:.4f}"
            f"\nText: {match['complaint_text']}"
        )