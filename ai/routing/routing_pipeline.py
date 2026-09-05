"""
Unified AI routing pipeline.

Pipeline:
Complaint
    -> Department prediction
    -> Category prediction
    -> Priority prediction
    -> Duplicate detection
    -> Department-filtered RAG
    -> Suggested resolution
    -> Final AI response
"""

from typing import Dict, Any, Tuple

from sklearn.model_selection import train_test_split

from ai.routing.semantic_department_classifier import (
    load_dataset,
    create_embeddings,
    predict_department,
)

from ai.routing.category_predictor import (
    prepare_category_model,
    predict_category,
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


# ============================================================
# PIPELINE CONFIGURATION
# ============================================================

RANDOM_SEED = 42
TEST_RATIO = 0.30

DEPARTMENT_TOP_K = 5
CATEGORY_TOP_K = 5
PRIORITY_TOP_K = 5
DUPLICATE_TOP_K = 5
RAG_TOP_K = 5


# ============================================================
# DEPARTMENT MODEL
# ============================================================

def prepare_department_model():
    """
    Prepare department training embeddings and labels.

    This is performed once and reused for all complaints.
    """

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

    return (
        training_embeddings,
        training_departments,
    )


# ============================================================
# CATEGORY MODEL
# ============================================================

def prepare_category_model_for_pipeline():
    """
    Prepare the category model once.

    Category prediction uses the full dataset as the
    semantic candidate pool and filters candidates by
    predicted department during prediction.
    """

    df = load_dataset()

    category_embeddings, category_df = (
        prepare_category_model(df)
    )

    return (
        category_embeddings,
        category_df,
    )


# ============================================================
# PRIORITY MODEL
# ============================================================

def prepare_priority_model():
    """
    Prepare the semantic priority model.

    The model is trained/evaluated once and then reused.
    """

    (
        model,
        train_embeddings,
        train_labels,
    ) = train_priority_model()

    return (
        model,
        train_embeddings,
        train_labels,
    )


# ============================================================
# COMPLETE AI PIPELINE
# ============================================================

def run_complete_ai_pipeline(
    complaint: str,
    department_model: Tuple[Any, Any],
    category_model: Tuple[Any, Any],
    priority_model: Tuple[Any, Any, Any],
) -> Dict[str, Any]:
    """
    Run the complete AI routing pipeline.

    Models are supplied from outside so they are prepared only
    once instead of being rebuilt for every complaint.
    """

    if not isinstance(complaint, str):
        raise ValueError(
            "complaint must be a string."
        )

    if not complaint.strip():
        raise ValueError(
            "complaint cannot be empty."
        )

    # ========================================================
    # 1. Unpack department model
    # ========================================================

    (
        department_training_embeddings,
        department_training_labels,
    ) = department_model

    # ========================================================
    # 2. Predict department
    # ========================================================

    (
        department,
        department_neighbours,
    ) = predict_department(
        complaint_text=complaint,
        training_embeddings=(
            department_training_embeddings
        ),
        training_departments=(
            department_training_labels
        ),
        k=DEPARTMENT_TOP_K,
    )

    # ========================================================
    # 3. Unpack category model
    # ========================================================

    (
        category_training_embeddings,
        category_training_df,
    ) = category_model

    # ========================================================
    # 4. Predict category
    # ========================================================

    (
        category,
        category_confidence,
        category_neighbours,
    ) = predict_category(
        complaint_text=complaint,
        predicted_department=department,
        training_embeddings=(
            category_training_embeddings
        ),
        training_df=category_training_df,
        k=CATEGORY_TOP_K,
    )

    # ========================================================
    # 5. Unpack priority model
    # ========================================================

    (
        priority_model_instance,
        priority_training_embeddings,
        priority_training_labels,
    ) = priority_model

    # ========================================================
    # 6. Predict priority
    # ========================================================

    (
        priority,
        priority_confidence,
        priority_neighbours,
    ) = predict_priority(
        complaint_text=complaint,
        model=priority_model_instance,
        train_embeddings=(
            priority_training_embeddings
        ),
        train_labels=(
            priority_training_labels
        ),
        top_k=PRIORITY_TOP_K,
    )

    # ========================================================
    # 7. Duplicate detection
    # ========================================================

    duplicate_result = find_similar_complaints(
        new_complaint=complaint,
        top_k=DUPLICATE_TOP_K,
    )

    # ========================================================
    # 8. Department-filtered RAG
    # ========================================================

    rag_result = run_rag_pipeline(
        complaint=complaint,
        top_k=RAG_TOP_K,
        department=department,
    )

    # ========================================================
    # 9. AI response
    # ========================================================

    rag_response = build_ai_response(
        complaint=complaint,
        similar_complaints=(
            rag_result["similar_complaints"]
        ),
        knowledge_documents=(
            rag_result["knowledge_documents"]
        ),
        retrieved_context=(
            rag_result["retrieved_context"]
        ),
        sources=(
            rag_result["sources"]
        ),
    )

    # ========================================================
    # 10. Final structured response
    # ========================================================

    return {
        "complaint": complaint,

        "prediction": {
            "department": department,
            "category": category,
            "category_confidence": category_confidence,
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

        "category_neighbours": category_neighbours,

        "priority_neighbours": priority_neighbours,

                "rag": {
            "similar_complaints": (
                rag_response["similar_complaints"]
            ),
            "knowledge_documents": (
                rag_response["knowledge_documents"]
            ),
            "retrieved_context": (
                rag_response["retrieved_context"]
            ),
            "suggested_resolution": (
                rag_response["suggested_resolution"]
            ),
            "sources": (
                rag_response["sources"]
            ),
            "model": (
                rag_response["model"]
            ),
        },

        "status": "PREDICTED",
    }


# ============================================================
# PRINT RESULT
# ============================================================

def print_result(
    result: Dict[str, Any],
    expected_department: str = "",
) -> None:
    """Print one pipeline result clearly."""

    print("\n" + "#" * 70)

    if expected_department:
        print(
            f"EXPECTED DEPARTMENT: "
            f"{expected_department}"
        )

    print("#" * 70)

    print("\nComplaint:")
    print(result["complaint"])

    print("\nPredicted Department:")
    print(
        result["prediction"]["department"]
    )

    print("\nPredicted Category:")
    print(
        result["prediction"]["category"]
    )

    print("\nCategory Confidence:")
    print(
        f"{result['prediction']['category_confidence']:.2f}"
    )

    print("\nPredicted Priority:")
    print(
        result["prediction"]["priority"]
    )

    print("\nPriority Confidence:")
    print(
        f"{result['prediction']['priority_confidence']:.2f}"
    )

    print("\nDuplicate Detection:")
    print(
        result["duplicate_detection"]["is_duplicate"]
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

    print("\nCategory Neighbours:")

    for neighbour in result[
        "category_neighbours"
    ]:

        print(
            f"- ID={neighbour['complaint_id']} | "
            f"category={neighbour['category']} | "
            f"similarity="
            f"{neighbour['similarity']:.4f}"
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

    print("\nRAG Model:")
    print(
        result["rag"]["model"]
    )

    print("\nSimilar Historical Complaints:")

    for complaint in result["rag"]["similar_complaints"]:

        print(
            f"- ID={complaint['complaint_id']} | "
            f"category={complaint['category']} | "
            f"similarity="
            f"{complaint['similarity']:.4f}"
        )

    print("\nKnowledge Documents:")

    for document in result["rag"]["knowledge_documents"]:

        print(
            f"- {document['source']} | "
            f"similarity="
            f"{document['similarity']:.4f}"
        )

    print("\nRAG Sources:")

    for source in result["rag"]["sources"]:

        print(
            f"- {source['type']} | "
            f"{source['source']} | "
            f"similarity="
            f"{source['similarity']:.4f}"
        )

    print("\nSuggested Resolution:")
    print(
        result["rag"]["suggested_resolution"]
    )

    print("\nStatus:")
    print(result["status"])


# ============================================================
# TEST THE FIVE DEPARTMENTS
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 70)
    print("PREPARING DEPARTMENT MODEL")
    print("=" * 70)

    department_model = (
        prepare_department_model()
    )

    print("\n" + "=" * 70)
    print("PREPARING CATEGORY MODEL")
    print("=" * 70)

    category_model = (
        prepare_category_model_for_pipeline()
    )

    print("\n" + "=" * 70)
    print("PREPARING PRIORITY MODEL")
    print("=" * 70)

    priority_model = (
        prepare_priority_model()
    )

    test_complaints = [
        (
            "Technical",
            "The internet connection in the computer laboratory "
            "is not working.",
        ),
        (
            "Finance",
            "I was charged the wrong amount for my semester fee.",
        ),
        (
            "Electrical",
            "The power has completely failed in the laboratory.",
        ),
        (
            "Plumbing",
            "There is a serious water pipe leak "
            "behind the hostel building.",
        ),
        (
            "Security",
            "Someone entered the hostel area "
            "without authorization.",
        ),
    ]

    print("\n" + "=" * 70)
    print("RUNNING FIVE-DEPARTMENT AI TEST")
    print("=" * 70)

    for expected_department, complaint in test_complaints:

        result = run_complete_ai_pipeline(
            complaint=complaint,
            department_model=department_model,
            category_model=category_model,
            priority_model=priority_model,
        )

        print_result(
            result,
            expected_department=expected_department,
        )