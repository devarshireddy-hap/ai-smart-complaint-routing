"""
Generate text embeddings for complaints.
"""

from typing import List

from ai.embeddings.embedding_model import load_embedding_model


def generate_embedding(text: str) -> List[float]:
    """
    Convert complaint text into a numerical embedding vector.

    Args:
        text: Complaint text.

    Returns:
        List of floating-point values representing the text embedding.

    Raises:
        ValueError: If the input text is empty.
    """

    if not isinstance(text, str):
        raise ValueError("Text must be a string.")

    text = text.strip()

    if not text:
        raise ValueError("Text cannot be empty.")

    model = load_embedding_model()

    embedding = model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    return embedding.tolist()