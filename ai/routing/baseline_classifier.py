"""
Traditional baseline for complaint department classification.

Pipeline:
Complaint text
    -> TF-IDF
    -> Logistic Regression
    -> Department prediction
"""

from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

RANDOM_SEED = 42

TRAIN_RATIO = 0.70
TEST_RATIO = 0.30

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "complaints.csv"
)


# ------------------------------------------------------------
# Load dataset
# ------------------------------------------------------------

def load_dataset() -> pd.DataFrame:
    """Load the complaint dataset from CSV."""

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

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    return df


# ------------------------------------------------------------
# Train baseline department classifier
# ------------------------------------------------------------

def train_department_classifier(
    df: pd.DataFrame,
):
    """
    Train a TF-IDF + Logistic Regression department classifier.

    Returns:
        vectorizer: Fitted TF-IDF vectorizer.
        model: Fitted Logistic Regression model.
        X_test: Test feature matrix.
        y_test: Test labels.
    """

    X = df["complaint_text"].astype(str)
    y = df["department"].astype(str)

    # Split the dataset.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_RATIO,
        random_state=RANDOM_SEED,
        stratify=y,
    )

    # Convert text into TF-IDF numerical features.
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # Train classifier.
    model = LogisticRegression(
        max_iter=1000,
        random_state=RANDOM_SEED,
    )

    model.fit(X_train_tfidf, y_train)

    return (
        vectorizer,
        model,
        X_test_tfidf,
        y_test,
        X_test,
    )


# ------------------------------------------------------------
# Evaluate model
# ------------------------------------------------------------

def evaluate_model(
    model,
    X_test_tfidf,
    y_test,
) -> None:
    """Print evaluation metrics for the baseline."""

    predictions = model.predict(X_test_tfidf)

    accuracy = accuracy_score(y_test, predictions)

    print("\n=== BASELINE RESULTS ===")
    print(f"Accuracy: {accuracy:.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, predictions))


# ------------------------------------------------------------
# Test a new complaint
# ------------------------------------------------------------

def predict_department(
    complaint_text: str,
    vectorizer,
    model,
) -> str:
    """
    Predict the department for a new complaint.
    """

    complaint_vector = vectorizer.transform(
        [complaint_text]
    )

    prediction = model.predict(
        complaint_vector
    )

    return str(prediction[0])


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main() -> None:

    df = load_dataset()

    print("Dataset loaded successfully.")
    print(f"Number of complaints: {len(df)}")

    print("\nDepartments:")
    print(df["department"].value_counts())

    (
        vectorizer,
        model,
        X_test_tfidf,
        y_test,
        X_test,
    ) = train_department_classifier(df)

    evaluate_model(
        model,
        X_test_tfidf,
        y_test,
    )

    # Example prediction.
    test_complaint = (
        "The water pipe near the hostel is leaking."
    )

    predicted_department = predict_department(
        test_complaint,
        vectorizer,
        model,
    )

    print("\n=== EXAMPLE PREDICTION ===")
    print(f"Complaint: {test_complaint}")
    print(f"Predicted Department: {predicted_department}")


if __name__ == "__main__":
    main()