from pathlib import Path

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

from ai.embeddings.embedding_model import load_embedding_model


DATASET_PATH = Path("data/complaints.csv")

TEST_SIZE = 0.30
RANDOM_STATE = 42
TOP_K = 5


def load_dataset() -> pd.DataFrame:
    """Load and validate the complaint dataset."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)

    required_columns = {
        "complaint_text",
        "priority",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Dataset is missing columns: {missing_columns}"
        )

    df = df.dropna(
        subset=["complaint_text", "priority"]
    )

    return df


def cosine_similarity(vector_a, vector_b) -> float:
    """Calculate cosine similarity between two vectors."""

    a = np.asarray(vector_a, dtype=float)
    b = np.asarray(vector_b, dtype=float)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)


def predict_priority_from_neighbors(
    similarities,
    labels,
    top_k=TOP_K,
):
    """Predict priority using majority voting among nearest neighbors."""

    top_indices = np.argsort(
        similarities
    )[-top_k:][::-1]

    top_labels = [
        labels[index]
        for index in top_indices
    ]

    counts = {}

    for label in top_labels:
        counts[label] = counts.get(label, 0) + 1

    # Highest vote count wins.
    # In case of a tie, use the highest total similarity.
    best_label = None
    best_vote_count = -1
    best_similarity_sum = -1.0

    for label in counts:

        vote_count = counts[label]

        similarity_sum = sum(
            similarities[index]
            for index in top_indices
            if labels[index] == label
        )

        if (
            vote_count > best_vote_count
            or (
                vote_count == best_vote_count
                and similarity_sum > best_similarity_sum
            )
        ):
            best_label = label
            best_vote_count = vote_count
            best_similarity_sum = similarity_sum

    return best_label


def train_and_evaluate():

    df = load_dataset()

    X = df["complaint_text"].astype(str).tolist()
    y = df["priority"].astype(str).tolist()

    print("\nPriority distribution:")
    print(pd.Series(y).value_counts())

    # Split BEFORE generating embeddings
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print("\nTraining examples:", len(X_train))
    print("Testing examples:", len(X_test))

    # Load embedding model once
    model = load_embedding_model()

    print("\nGenerating training embeddings...")

    train_embeddings = model.encode(
        X_train,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    print("Generating test embeddings...")

    test_embeddings = model.encode(
        X_test,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    predictions = []

    for test_embedding in test_embeddings:

        similarities = np.dot(
            train_embeddings,
            test_embedding
        )

        prediction = predict_priority_from_neighbors(
            similarities,
            y_train,
            top_k=TOP_K,
        )

        predictions.append(prediction)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    print("\n" + "=" * 55)
    print("SEMANTIC PRIORITY CLASSIFIER")
    print("=" * 55)

    print(f"\nAccuracy: {accuracy:.4f}")

    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    return model, train_embeddings, y_train


def predict_priority(
    complaint_text: str,
    model,
    train_embeddings,
    train_labels,
    top_k=TOP_K,
):
    """Predict priority and return a confidence estimate."""

    if not isinstance(complaint_text, str):
        raise ValueError(
            "complaint_text must be a string."
        )

    if not complaint_text.strip():
        raise ValueError(
            "complaint_text cannot be empty."
        )

    complaint_embedding = model.encode(
        complaint_text,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    similarities = np.dot(
        train_embeddings,
        complaint_embedding
    )

    # Find the nearest examples
    top_indices = np.argsort(
        similarities
    )[-top_k:][::-1]

    nearest_examples = []

    for index in top_indices:

        nearest_examples.append(
            {
                "similarity": float(
                    similarities[index]
                ),
                "priority": train_labels[index],
            }
        )

    # Count votes for each priority
    vote_counts = {}

    for index in top_indices:

        label = train_labels[index]

        vote_counts[label] = (
            vote_counts.get(label, 0) + 1
        )

    # Select the priority with the most votes
    predicted_priority = max(
        vote_counts,
        key=vote_counts.get,
    )

    # Prototype confidence:
    # percentage of nearest neighbors
    # that voted for the predicted priority
    confidence = (
        vote_counts[predicted_priority]
        / len(top_indices)
    )

    return (
        predicted_priority,
        confidence,
        nearest_examples,
    )


if __name__ == "__main__":

    model, train_embeddings, train_labels = (
        train_and_evaluate()
    )

    test_complaints = [
        "There is a major water pipe leak in the hostel.",
        "I need clarification about my fee payment.",
        "The electrical power has completely failed in the laboratory.",
        "Someone has entered the hostel without authorization.",
    ]

    print("\nExample Predictions:")

    for complaint in test_complaints:

        priority, confidence, nearest_examples = (
            predict_priority(
                complaint,
                model,
                train_embeddings,
                train_labels,
            )
        )

        print("\nComplaint:")
        print(complaint)

        print(
            f"Predicted Priority: {priority}"
        )

        print(
            f"Confidence: {confidence:.2f}"
        )

        print("Nearest examples:")

        for example in nearest_examples:

            print(
                f"  similarity={example['similarity']:.4f}, "
                f"priority={example['priority']}"
            )