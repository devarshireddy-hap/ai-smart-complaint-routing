from pathlib import Path

import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


DATASET_PATH = Path("data/complaints.csv")

TEST_SIZE = 0.30
RANDOM_STATE = 42


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


def train_priority_classifier():

    df = load_dataset()

    X = df["complaint_text"].astype(str)
    y = df["priority"].astype(str)

    print("\nPriority distribution:")
    print(y.value_counts())

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        lowercase=True,
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    classifier = LogisticRegression(
        max_iter=1000,
        random_state=RANDOM_STATE,
    )

    classifier.fit(
        X_train_tfidf,
        y_train,
    )

    predictions = classifier.predict(
        X_test_tfidf
    )

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    print("\n" + "=" * 50)
    print("PRIORITY CLASSIFIER EVALUATION")
    print("=" * 50)

    print(f"\nAccuracy: {accuracy:.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    return vectorizer, classifier


def predict_priority(
    complaint_text: str,
    vectorizer,
    classifier,
) -> str:
    """Predict priority for a new complaint."""

    if not isinstance(complaint_text, str):
        raise ValueError(
            "complaint_text must be a string."
        )

    if not complaint_text.strip():
        raise ValueError(
            "complaint_text cannot be empty."
        )

    complaint_vector = vectorizer.transform(
        [complaint_text]
    )

    prediction = classifier.predict(
        complaint_vector
    )

    return str(prediction[0])


if __name__ == "__main__":

    vectorizer, classifier = (
        train_priority_classifier()
    )

    test_complaints = [
        "There is a major water pipe leak in the hostel.",
        "I need clarification about my fee payment.",
        "The electrical power has failed in the laboratory.",
    ]

    print("\nExample Predictions:")

    for complaint in test_complaints:

        priority = predict_priority(
            complaint,
            vectorizer,
            classifier,
        )

        print(f"\nComplaint: {complaint}")
        print(f"Predicted Priority: {priority}")