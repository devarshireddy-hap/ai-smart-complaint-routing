"""
Final AI evaluation.

Evaluation split:
    70% training
    approximately 15% validation
    approximately 15% test

For the current 50-row dataset:
    Training   = 35 rows (70%)
    Validation = 8 rows  (16%)
    Testing    = 7 rows  (14%)

Models evaluated:
    1. Department prediction
    2. Category prediction
    3. Priority prediction

Evaluation method:
    Semantic embeddings + cosine similarity +
    nearest-neighbour majority voting.

The test set is never used when building the training pool
or selecting the best k value.

No keyword or string matching is used.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
)

from ai.embeddings.embedding_generator import (
    generate_embedding,
)


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42

TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TEST_RATIO = 0.15

TOP_K_VALUES = [1, 3, 5]

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "complaints.csv"
)


# ============================================================
# DATASET
# ============================================================

def load_dataset() -> pd.DataFrame:
    """Load and validate the complaint dataset."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

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
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df.empty:
        raise ValueError(
            "The complaint dataset is empty."
        )

    df = df.dropna(
        subset=[
            "complaint_text",
            "department",
            "category",
            "priority",
        ]
    ).reset_index(drop=True)

    return df


# ============================================================
# EMBEDDINGS
# ============================================================

def create_embeddings(
    texts,
) -> np.ndarray:
    """
    Generate normalized sentence embeddings.
    """

    embeddings = [
        generate_embedding(str(text))
        for text in texts
    ]

    return np.asarray(
        embeddings,
        dtype=np.float32,
    )


# ============================================================
# DATA SPLITTING
# ============================================================

def create_data_splits(
    df: pd.DataFrame,
):
    """
    Create train, validation, and test datasets.

    For the current 50-row dataset:
        Training   = 35
        Validation = 8
        Testing    = 7

    This is the closest whole-number representation of
    the required 70/15/15 split.
    """

    # --------------------------------------------------------
    # Training = 35 rows
    # --------------------------------------------------------

    train_df, temporary_df = train_test_split(
        df,
        train_size=35,
        random_state=RANDOM_SEED,
        stratify=df["department"],
    )

    # --------------------------------------------------------
    # Validation = 8 rows
    # Test = 7 rows
    # --------------------------------------------------------

    validation_df, test_df = train_test_split(
        temporary_df,
        train_size=8,
        test_size=7,
        random_state=RANDOM_SEED,
        stratify=temporary_df["department"],
    )

    return (
        train_df.reset_index(drop=True),
        validation_df.reset_index(drop=True),
        test_df.reset_index(drop=True),
    )


# ============================================================
# NEAREST-NEIGHBOUR PREDICTION
# ============================================================

def predict_label(
    complaint: str,
    training_embeddings: np.ndarray,
    training_labels,
    k: int,
):
    """
    Predict a label using semantic nearest neighbours.

    Embeddings are normalized, therefore their dot product
    is equivalent to cosine similarity.
    """

    query_embedding = np.asarray(
        generate_embedding(complaint),
        dtype=np.float32,
    )

    similarities = (
        training_embeddings
        @ query_embedding
    )

    k = min(
        k,
        len(training_labels),
    )

    top_indices = np.argsort(
        similarities
    )[-k:][::-1]

    labels = [
        training_labels[index]
        for index in top_indices
    ]

    vote_counts = {}

    for label in labels:
        vote_counts[label] = (
            vote_counts.get(label, 0) + 1
        )

    # --------------------------------------------------------
    # Majority vote
    # --------------------------------------------------------

    predicted_label = max(
        vote_counts,
        key=vote_counts.get,
    )

    return predicted_label


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    y_true,
    y_pred,
):
    """
    Calculate accuracy, macro precision, macro recall,
    and macro F1.
    """

    accuracy = accuracy_score(
        y_true,
        y_pred,
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            y_true,
            y_pred,
            average="macro",
            zero_division=0,
        )
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


# ============================================================
# DEPARTMENT EVALUATION
# ============================================================

def evaluate_department(
    train_df: pd.DataFrame,
    evaluation_df: pd.DataFrame,
    k: int,
):
    """
    Evaluate semantic department prediction.
    """

    training_embeddings = create_embeddings(
        train_df["complaint_text"].tolist()
    )

    training_labels = (
        train_df["department"]
        .astype(str)
        .tolist()
    )

    predictions = []

    for complaint in evaluation_df["complaint_text"]:

        prediction = predict_label(
            complaint=str(complaint),
            training_embeddings=training_embeddings,
            training_labels=training_labels,
            k=k,
        )

        predictions.append(prediction)

    actual = (
        evaluation_df["department"]
        .astype(str)
        .tolist()
    )

    metrics = calculate_metrics(
        actual,
        predictions,
    )

    return metrics, predictions


# ============================================================
# CATEGORY EVALUATION
# ============================================================

def evaluate_category(
    train_df: pd.DataFrame,
    evaluation_df: pd.DataFrame,
    k: int,
):
    """
    Evaluate semantic category prediction.

    Category candidates are restricted to the TRUE department
    during this isolated category evaluation.

    This measures the category classifier independently rather
    than combining department errors with category errors.
    """

    training_embeddings = create_embeddings(
        train_df["complaint_text"].tolist()
    )

    predictions = []
    actual = []

    for _, row in evaluation_df.iterrows():

        true_department = str(
            row["department"]
        )

        department_mask = (
            train_df["department"]
            .astype(str)
            == true_department
        )

        department_indices = np.where(
            department_mask.to_numpy()
        )[0]

        if len(department_indices) == 0:
            continue

        department_embeddings = (
            training_embeddings[
                department_indices
            ]
        )

        department_categories = (
            train_df.iloc[
                department_indices
            ]["category"]
            .astype(str)
            .tolist()
        )

        prediction = predict_label(
            complaint=str(
                row["complaint_text"]
            ),
            training_embeddings=department_embeddings,
            training_labels=department_categories,
            k=k,
        )

        predictions.append(prediction)
        actual.append(
            str(row["category"])
        )

    metrics = calculate_metrics(
        actual,
        predictions,
    )

    return (
        metrics,
        predictions,
        actual,
    )


# ============================================================
# PRIORITY EVALUATION
# ============================================================

def evaluate_priority(
    train_df: pd.DataFrame,
    evaluation_df: pd.DataFrame,
    k: int,
):
    """
    Evaluate semantic priority prediction.
    """

    training_embeddings = create_embeddings(
        train_df["complaint_text"].tolist()
    )

    training_labels = (
        train_df["priority"]
        .astype(str)
        .tolist()
    )

    predictions = []

    for complaint in evaluation_df["complaint_text"]:

        prediction = predict_label(
            complaint=str(complaint),
            training_embeddings=training_embeddings,
            training_labels=training_labels,
            k=k,
        )

        predictions.append(prediction)

    actual = (
        evaluation_df["priority"]
        .astype(str)
        .tolist()
    )

    metrics = calculate_metrics(
        actual,
        predictions,
    )

    return metrics, predictions


# ============================================================
# VALIDATION: SELECT BEST K
# ============================================================

def choose_best_k(
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
):
    """
    Select the best k independently for department,
    category, and priority using validation data only.
    """

    print("\n" + "=" * 70)
    print("VALIDATION: SELECTING BEST K")
    print("=" * 70)

    results = {}

    # --------------------------------------------------------
    # Department
    # --------------------------------------------------------

    best_department_k = None
    best_department_score = -1.0

    for k in TOP_K_VALUES:

        metrics, _ = evaluate_department(
            train_df,
            validation_df,
            k,
        )

        print(
            f"\nDepartment k={k}: "
            f"F1={metrics['f1']:.4f}"
        )

        if metrics["f1"] > best_department_score:

            best_department_score = (
                metrics["f1"]
            )

            best_department_k = k

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    best_category_k = None
    best_category_score = -1.0

    for k in TOP_K_VALUES:

        metrics, _, _ = evaluate_category(
            train_df,
            validation_df,
            k,
        )

        print(
            f"Category k={k}: "
            f"F1={metrics['f1']:.4f}"
        )

        if metrics["f1"] > best_category_score:

            best_category_score = (
                metrics["f1"]
            )

            best_category_k = k

    # --------------------------------------------------------
    # Priority
    # --------------------------------------------------------

    best_priority_k = None
    best_priority_score = -1.0

    for k in TOP_K_VALUES:

        metrics, _ = evaluate_priority(
            train_df,
            validation_df,
            k,
        )

        print(
            f"Priority k={k}: "
            f"F1={metrics['f1']:.4f}"
        )

        if metrics["f1"] > best_priority_score:

            best_priority_score = (
                metrics["f1"]
            )

            best_priority_k = k

    results["department"] = best_department_k
    results["category"] = best_category_k
    results["priority"] = best_priority_k

    print("\nSelected k values:")

    print(
        f"Department: {best_department_k}"
    )

    print(
        f"Category:   {best_category_k}"
    )

    print(
        f"Priority:   {best_priority_k}"
    )

    return results


# ============================================================
# MAIN EVALUATION
# ============================================================

def main():

    print("\n" + "=" * 70)
    print("FINAL AI EVALUATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    df = load_dataset()

    # --------------------------------------------------------
    # Create data splits
    # --------------------------------------------------------

    (
        train_df,
        validation_df,
        test_df,
    ) = create_data_splits(df)

    # --------------------------------------------------------
    # Print split information
    # --------------------------------------------------------

    print("\nDataset:")

    print(
        f"Total examples: {len(df)}"
    )

    print(
        f"Training:       {len(train_df)} "
        f"({len(train_df) / len(df):.0%})"
    )

    print(
        f"Validation:     {len(validation_df)} "
        f"({len(validation_df) / len(df):.0%})"
    )

    print(
        f"Testing:        {len(test_df)} "
        f"({len(test_df) / len(df):.0%})"
    )

    # --------------------------------------------------------
    # Select k using validation set
    # --------------------------------------------------------

    best_k = choose_best_k(
        train_df,
        validation_df,
    )

    # --------------------------------------------------------
    # FINAL TEST RESULTS
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL TEST RESULTS")
    print("=" * 70)

    # ========================================================
    # DEPARTMENT
    # ========================================================

    (
        department_metrics,
        department_predictions,
    ) = evaluate_department(
        train_df,
        test_df,
        best_k["department"],
    )

    print("\nDEPARTMENT")

    print(
        f"Accuracy : "
        f"{department_metrics['accuracy']:.4f}"
    )

    print(
        f"Precision: "
        f"{department_metrics['precision']:.4f}"
    )

    print(
        f"Recall   : "
        f"{department_metrics['recall']:.4f}"
    )

    print(
        f"F1       : "
        f"{department_metrics['f1']:.4f}"
    )

    # ========================================================
    # CATEGORY
    # ========================================================

    (
        category_metrics,
        category_predictions,
        category_actual,
    ) = evaluate_category(
        train_df,
        test_df,
        best_k["category"],
    )

    print("\nCATEGORY")

    print(
        f"Accuracy : "
        f"{category_metrics['accuracy']:.4f}"
    )

    print(
        f"Precision: "
        f"{category_metrics['precision']:.4f}"
    )

    print(
        f"Recall   : "
        f"{category_metrics['recall']:.4f}"
    )

    print(
        f"F1       : "
        f"{category_metrics['f1']:.4f}"
    )

    print(
        "\nNote: Category evaluation uses the TRUE department "
        "to isolate category prediction performance."
    )

    # ========================================================
    # PRIORITY
    # ========================================================

    (
        priority_metrics,
        priority_predictions,
    ) = evaluate_priority(
        train_df,
        test_df,
        best_k["priority"],
    )

    print("\nPRIORITY")

    print(
        f"Accuracy : "
        f"{priority_metrics['accuracy']:.4f}"
    )

    print(
        f"Precision: "
        f"{priority_metrics['precision']:.4f}"
    )

    print(
        f"Recall   : "
        f"{priority_metrics['recall']:.4f}"
    )

    print(
        f"F1       : "
        f"{priority_metrics['f1']:.4f}"
    )

    # ========================================================
    # CATEGORY CLASSIFICATION REPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("CATEGORY CLASSIFICATION REPORT")
    print("=" * 70)

    print(
        classification_report(
            category_actual,
            category_predictions,
            zero_division=0,
        )
    )

    # ========================================================
    # PRIORITY CLASSIFICATION REPORT
    # ========================================================

    print("=" * 70)
    print("PRIORITY CLASSIFICATION REPORT")
    print("=" * 70)

    print(
        classification_report(
            test_df["priority"].astype(str),
            priority_predictions,
            zero_division=0,
        )
    )

    # ========================================================
    # DEPARTMENT CLASSIFICATION REPORT
    # ========================================================

    print("=" * 70)
    print("DEPARTMENT CLASSIFICATION REPORT")
    print("=" * 70)

    print(
        classification_report(
            test_df["department"].astype(str),
            department_predictions,
            zero_division=0,
        )
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    print(
        f"Best Department k : "
        f"{best_k['department']}"
    )

    print(
        f"Best Category k   : "
        f"{best_k['category']}"
    )

    print(
        f"Best Priority k   : "
        f"{best_k['priority']}"
    )

    print(
        f"\nDepartment Accuracy : "
        f"{department_metrics['accuracy']:.4f}"
    )

    print(
        f"Department F1       : "
        f"{department_metrics['f1']:.4f}"
    )

    print(
        f"\nCategory Accuracy   : "
        f"{category_metrics['accuracy']:.4f}"
    )

    print(
        f"Category F1         : "
        f"{category_metrics['f1']:.4f}"
    )

    print(
        f"\nPriority Accuracy   : "
        f"{priority_metrics['accuracy']:.4f}"
    )

    print(
        f"Priority F1         : "
        f"{priority_metrics['f1']:.4f}"
    )

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()