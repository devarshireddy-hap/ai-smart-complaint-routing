"""
Unified AI routing pipeline.

Current pipeline:
Complaint
    -> Department prediction
    -> Priority prediction
    -> Duplicate detection
    -> RAG retrieval
    -> Suggested resolution
    -> Final AI response
"""

from typing import Dict, Any

from sklearn.model_selection import train_test_split

from ai.routing.semantic_department_classifier import (
    load_dataset,
    create_embeddings,
    predict_department,
)

from ai.routing.semantic_priority_classifier import (
    train_and_evaluate as train_priority_model,
    predict_priority,
)

from ai.routing.duplicate_detector import (
    find_similar_complaints,
)

from ai.rag.rag_pipeline import (
    run_rag_pipeline,
)

from ai.rag.rag_response import (
    build_ai_response,
)


RANDOM_SEED = 42
TEST_RATIO = 0.30

DEPARTMENT_TOP_K = 5
PRIORITY_TOP_K = 5
DUPLICATE_TOP_K = 5
RAG_TOP_K = 3


def prepare_department_model():
    """Prepare department training embeddings."""

    df = load_dataset()

    train_df, _ = train_test_split(
        df,
        test_size=TEST_RATIO,
        random_state=RANDOM_SEED,
        stratify=df["department"],
    )

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

    return training_embeddings, training_departments


def prepare_priority_model():
    """Prepare semantic priority model."""

    model, train_embeddings, train_labels = (
        train_priority_model()
    )

    return model, train_embeddings, train_labels


def run_complete_ai_pipeline(
    complaint: str,
) -> Dict[str, Any]:
    """Run the complete AI routing prototype."""

    if not isinstance(complaint, str):
        raise ValueError(
            "complaint must be a string."
        )

    if not complaint.strip():
        raise ValueError(
            "complaint cannot be empty."
        )

    # =========================================
    # 1. Department prediction
    # =========================================

    (
        department_training_embeddings,
        department_training_labels,
    ) = prepare_department_model()

    department, department_neighbours = (
        predict_department(
            complaint_text=complaint,
            training_embeddings=(
                department_training_embeddings
            ),
            training_departments=(
                department_training_labels
            ),
            k=DEPARTMENT_TOP_K,
        )
    )

    # =========================================
    # 2. Priority prediction
    # =========================================

    (
        priority_model,
        priority_training_embeddings,
        priority_training_labels,
    ) = prepare_priority_model()

    (
        priority,
        priority_confidence,
        priority_neighbours,
    ) = predict_priority(
        complaint_text=complaint,
        model=priority_model,
        train_embeddings=priority_training_embeddings,
        train_labels=priority_training_labels,
        top_k=PRIORITY_TOP_K,
    )

    # =========================================
    # 3. Duplicate detection
    # =========================================

    duplicate_result = find_similar_complaints(
        new_complaint=complaint,
        top_k=DUPLICATE_TOP_K,
    )

    # =========================================
    # 4. RAG retrieval
    # =========================================

    rag_result = run_rag_pipeline(
    complaint=complaint,
    top_k=RAG_TOP_K,
    department=department,
)

    # =========================================
    # 5. Suggested response
    # =========================================

    rag_response = build_ai_response(
        complaint=complaint,
        retrieved_documents=(
            rag_result["retrieved_documents"]
        ),
    )

    # =========================================
    # 6. Final response
    # =========================================

    return {
        "complaint": complaint,

        "prediction": {
            "department": department,
            "priority": priority,
            "priority_confidence": priority_confidence,
        },

        "duplicate_detection": {
            "is_duplicate": duplicate_result[
                "is_duplicate"
            ],
            "matches": duplicate_result[
                "top_matches"
            ],
        },

        "department_neighbours": [
            {
                "department": dept,
                "similarity": similarity,
            }
            for dept, similarity
            in department_neighbours
        ],

        "priority_neighbours": priority_neighbours,

        "rag": {
            "sources": rag_response["sources"],
            "suggested_resolution": (
                rag_response["suggested_resolution"]
            ),
        },

        "status": "PREDICTED",
    }


def print_result(result: Dict[str, Any]) -> None:
    """Print the AI pipeline result clearly."""

    print("\n" + "=" * 60)
    print("COMPLETE AI ROUTING PIPELINE")
    print("=" * 60)

    print("\nComplaint:")
    print(result["complaint"])

    print("\nPrediction:")
    print(
        f"Department: "
        f"{result['prediction']['department']}"
    )
    print(
        f"Priority: "
        f"{result['prediction']['priority']}"
    )
    print(
        f"Priority Confidence: "
        f"{result['prediction']['priority_confidence']:.2f}"
    )

    print("\nDuplicate Detection:")
    print(
        f"Is Duplicate: "
        f"{result['duplicate_detection']['is_duplicate']}"
    )

    print("\nTop Duplicate Matches:")

    for match in result[
        "duplicate_detection"
    ]["matches"]:

        print(
            f"- ID={match['complaint_id']}, "
            f"similarity={match['similarity']:.4f}, "
            f"department={match['department']}"
        )

    print("\nDepartment Neighbours:")

    for neighbour in result[
        "department_neighbours"
    ]:

        print(
            f"- {neighbour['department']} "
            f"(similarity="
            f"{neighbour['similarity']:.4f})"
        )

    print("\nPriority Neighbours:")

    for neighbour in result[
        "priority_neighbours"
    ]:

        print(
            f"- {neighbour['priority']} "
            f"(similarity="
            f"{neighbour['similarity']:.4f})"
        )

    print("\nRAG Sources:")

    for source in result["rag"]["sources"]:

        print(
            f"- {source['source']} "
            f"(similarity="
            f"{source['similarity']:.4f})"
        )

    print("\nSuggested Resolution:")
    print(
        result["rag"]["suggested_resolution"]
    )

    print("\nStatus:")
    print(result["status"])


if __name__ == "__main__":

    test_complaint = (
        "There is a serious water pipe leak "
        "behind the hostel building."
    )

    result = run_complete_ai_pipeline(
        complaint=test_complaint,
    )

    print_result(result)