"""
Embedding model configuration and loading.

This module will be responsible for loading the text embedding
model used by the complaint routing system.
"""

from sentence_transformers import SentenceTransformer

from ai.config import EMBEDDING_MODEL_NAME


def load_embedding_model() -> SentenceTransformer:
    """
    Load and return the configured embedding model.

    Returns:
        SentenceTransformer: Loaded embedding model.
    """
    if EMBEDDING_MODEL_NAME == "TBD":
        raise ValueError(
            "EMBEDDING_MODEL_NAME has not been configured yet."
        )

    return SentenceTransformer(EMBEDDING_MODEL_NAME)