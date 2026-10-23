"""
Embedding model configuration and loading.

This module loads the text embedding model used by the
complaint routing system and reuses the same model instance
during the lifetime of the Python process.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from ai.config import EMBEDDING_MODEL_NAME


@lru_cache(maxsize=1)
def load_embedding_model() -> SentenceTransformer:
    """
    Load and return the configured embedding model.

    The model is cached after the first load, so repeated calls
    to this function reuse the same model instead of loading it
    again.

    Returns:
        SentenceTransformer: Loaded embedding model.
    """

    if EMBEDDING_MODEL_NAME == "TBD":
        raise ValueError(
            "EMBEDDING_MODEL_NAME has not been configured yet."
        )

    print(
        f"Loading embedding model: "
        f"{EMBEDDING_MODEL_NAME}"
    )

    return SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )