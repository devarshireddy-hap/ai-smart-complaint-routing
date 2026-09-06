"""
Semantic department classifier.

This classifier uses sentence embeddings and cosine similarity
instead of keyword or string matching.

Pipeline:
Complaint
    -> Embedding
    -> Similarity search against training complaints
    -> Nearest neighbours
    -> Department prediction
"""

from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from ai.embeddings.embedding_generator import generate_embedding


RANDOM_SEED = 42
TEST_RATIO = 0.30

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "complaints.csv"
)


def load_dataset() -> pd.DataFrame:
    """Load and validate the complaint dataset."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    required_columns = {
        "complaint_id",
        "complaint_text",
        "department",
        "category",
        "priority",
        "resolution",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    return df


def create_embeddings(
    texts: List[str],
) -> np.ndarray:
    """
    Generate one embedding vector for each text.
    """

    embeddings = [
        generate_embedding(text)
        for text in texts
    ]

    return np.array(embeddings)


def predict_department(
    complaint_text: str,
    training_embeddings: np.ndarray,
    training_departments: List[str],
    k: int = 5,
) -> Tuple[str, List[Tuple[str, float]]]:
    """
    Predict department using semantic nearest neighbours.

    Args:
        complaint_text: New complaint.
        training_embeddings: Embeddings from training complaints.
        training_departments: Department for each training embedding.
        k: Number of nearest complaints to inspect.

    Returns:
        Predicted department and ranked neighbours.
    """

    query_embedding = np.array(
        generate_embedding(complaint_text)
    )

    # Because our embeddings are normalized,
    # dot product corresponds to cosine similarity.
    similarities = training_embeddings @ query_embedding

    k = min(k, len(similarities))

    top_indices = np.argsort(
        similarities
    )[-k:][::-1]

    neighbours = []

    for index in top_indices:
        neighbours.append(
            (
                training_departments[index],
                float(similarities[index]),
            )
        )

    # Simple majority vote among the nearest neighbours.
    department_votes = {}

    for department, _ in neighbours:
        department_votes[department] = (
            department_votes.get(department, 0) + 1
        )

    predicted_department = max(
        department_votes,
        key=department_votes.get,
    )

    return predicted_department, neighbours


def main() -> None:

    df = load_dataset()

    print("Dataset loaded.")
    print(f"Total complaints: {len(df)}")

    # Split BEFORE generating embeddings.
    train_df, test_df = train_test_split(
        df,
        test_size=TEST_RATIO,
        random_state=RANDOM_SEED,
        stratify=df["department"],
    )

    print(f"Training complaints: {len(train_df)}")
    print(f"Testing complaints: {len(test_df)}")

    # Generate embeddings ONLY from training data.
    training_embeddings = create_embeddings(
        train_df["complaint_text"]
        .astype(str)
        .tolist()
    )

    training_departments = (
        train_df["department"]
        .astype(str)
        .tolist()
    )

    predictions = []

    for complaint in test_df["complaint_text"]:
        predicted, neighbours = predict_department(
            str(complaint),
            training_embeddings,
            training_departments,
            k=5,
        )

        predictions.append(predicted)

    actual = (
        test_df["department"]
        .astype(str)
        .tolist()
    )

    accuracy = accuracy_score(
        actual,
        predictions,
    )

    print("\n=== SEMANTIC MODEL RESULTS ===")
    print(f"Accuracy: {accuracy:.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            actual,
            predictions,
            zero_division=0,
        )
    )

    print("\nConfusion Matrix:")
    print(
        confusion_matrix(
            actual,
            predictions,
        )
    )

    # Example semantic prediction.
    example = (
        "There is a pipeline leak beside the hostel."
    )

    predicted, neighbours = predict_department(
        example,
        training_embeddings,
        training_departments,
        k=5,
    )

    print("\n=== EXAMPLE SEMANTIC PREDICTION ===")
    print(f"Complaint: {example}")
    print(f"Predicted Department: {predicted}")

    print("\nNearest Training Complaints:")
    for department, similarity in neighbours:
        print(
            f"Department={department}, "
            f"Similarity={similarity:.4f}"
        )


if __name__ == "__main__":
    main()