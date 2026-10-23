"""
Semantic category predictor.

Category prediction happens AFTER department prediction.

Pipeline:
Complaint
    -> Embedding
    -> Compare with training complaints
    -> Filter to predicted department
    -> Nearest neighbours
    -> Category prediction

No keyword or string matching is used.
"""

from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd

from ai.embeddings.embedding_generator import generate_embedding


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "complaints.csv"
)

TOP_K = 5


def load_dataset() -> pd.DataFrame:
    """Load and validate the complaints dataset."""

    df = pd.read_csv(DATA_PATH)

    required_columns = [
        "complaint_id",
        "complaint_text",
        "department",
        "category",
        "priority",
        "resolution",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    return df


def create_embeddings(texts: List[str]) -> np.ndarray:
    """Create normalized embeddings for complaint texts."""

    embeddings = [
        generate_embedding(text)
        for text in texts
    ]

    return np.array(embeddings)


def prepare_category_model(
    df: pd.DataFrame,
) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Prepare embeddings for category prediction.

    The full dataframe is retained so that the predicted
    department can later be used to filter candidates.
    """

    embeddings = create_embeddings(
        df["complaint_text"].tolist()
    )

    return embeddings, df


def predict_category(
    complaint_text: str,
    predicted_department: str,
    training_embeddings: np.ndarray,
    training_df: pd.DataFrame,
    k: int = TOP_K,
):
    """
    Predict category using semantic similarity.

    Only complaints belonging to the predicted department
    are considered.
    """

    department_mask = (
        training_df["department"].str.upper()
        == predicted_department.upper()
    )

    department_df = training_df[department_mask].copy()

    if department_df.empty:
        raise ValueError(
            f"No training complaints found for department: "
            f"{predicted_department}"
        )

    department_indices = department_df.index.to_numpy()

    department_embeddings = training_embeddings[
        department_indices
    ]

    query_embedding = np.array(
        generate_embedding(complaint_text)
    )

    similarities = (
        department_embeddings @ query_embedding
    )

    k = min(k, len(department_df))

    top_positions = np.argsort(similarities)[-k:][::-1]

    neighbours = []

    for position in top_positions:
        row_index = department_indices[position]

        neighbours.append(
            {
                "complaint_id": int(
                    training_df.loc[
                        row_index, "complaint_id"
                    ]
                ),
                "category": training_df.loc[
                    row_index, "category"
                ],
                "similarity": float(
                    similarities[position]
                ),
            }
        )

    category_votes = {}

    for neighbour in neighbours:
        category = neighbour["category"]

        category_votes[category] = (
            category_votes.get(category, 0) + 1
        )

    predicted_category = max(
        category_votes,
        key=category_votes.get
    )

    confidence = (
        category_votes[predicted_category] / len(neighbours)
    )

    return (
        predicted_category,
        confidence,
        neighbours,
    )


if __name__ == "__main__":

    print("=" * 60)
    print("CATEGORY PREDICTION TEST")
    print("=" * 60)

    df = load_dataset()

    print("\nCategory distribution:")
    print(
        df.groupby("department")["category"]
        .value_counts()
        .to_string()
    )

    print("\nPreparing category model...")

    embeddings, training_df = prepare_category_model(df)

    test_cases = [
        (
            "The Wi-Fi connection is not working in the hostel.",
            "Technical",
        ),
        (
            "The student payment is not reflected in the portal.",
            "Finance",
        ),
        (
            "There is a water pipe leak near Block B.",
            "Plumbing",
        ),
        (
            "The lights in the corridor are not working.",
            "Electrical",
        ),
        (
            "Someone entered the restricted area without permission.",
            "Security",
        ),
    ]

    for complaint, department in test_cases:

        category, confidence, neighbours = predict_category(
            complaint_text=complaint,
            predicted_department=department,
            training_embeddings=embeddings,
            training_df=training_df,
            k=TOP_K,
        )

        print("\n" + "-" * 60)
        print(f"Complaint   : {complaint}")
        print(f"Department  : {department}")
        print(f"Category    : {category}")
        print(f"Confidence  : {confidence:.2f}")

        print("\nNearest examples:")

        for neighbour in neighbours:
            print(
                f"  ID={neighbour['complaint_id']} | "
                f"Category={neighbour['category']} | "
                f"Similarity={neighbour['similarity']:.4f}"
            )