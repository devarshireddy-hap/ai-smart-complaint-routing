"""
Global configuration for the AI Smart Complaint Routing System.

This file contains shared AI, RAG, retrieval, duplicate-detection,
and evaluation settings.

Do not put passwords, API keys, or database credentials here.
"""

# ============================================================
# AI MODEL CONFIGURATION
# ============================================================

# Name of the text embedding model.
# TBD = model will be selected after testing candidate models.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# Name of the model used for complaint classification.
CLASSIFIER_MODEL_NAME = "TBD"

# Name of the LLM used for RAG-generated responses.
LLM_MODEL_NAME = "TBD"

# Version of our AI pipeline.
MODEL_VERSION = "v1.0"


# ============================================================
# VECTOR SEARCH CONFIGURATION
# ============================================================

# Number of similar records retrieved for RAG.
RAG_TOP_K = 5

# Number of similar complaints checked for possible duplicates.
DUPLICATE_TOP_K = 5

# Similarity metric used for semantic vector comparison.
SIMILARITY_METRIC = "cosine"

# Threshold for duplicate detection.
# Keep this as None until we experimentally determine the value.
DUPLICATE_SIMILARITY_THRESHOLD = None


# ============================================================
# AI FEATURE FLAGS
# ============================================================

# Enable/disable AI-based complaint routing.
ENABLE_AI_ROUTING = True

# Enable/disable semantic duplicate detection.
ENABLE_DUPLICATE_DETECTION = True

# Enable/disable Retrieval-Augmented Generation.
ENABLE_RAG = True

# Enable/disable human feedback on AI predictions.
ENABLE_AI_FEEDBACK = True


# ============================================================
# COMPLAINT PRIORITY LEVELS
# ============================================================

PRIORITY_LOW = "LOW"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_HIGH = "HIGH"
PRIORITY_URGENT = "URGENT"


# ============================================================
# OPTIONAL SEVERITY LEVELS
# ============================================================

# Keep these only if the team confirms severity is part
# of the final project scope.

SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"


# ============================================================
# USER ROLES
# ============================================================

ROLE_STUDENT = "STUDENT"
ROLE_FACULTY = "FACULTY"
ROLE_WORKING_STAFF = "WORKING_STAFF"
ROLE_ADMIN = "ADMIN"


# ============================================================
# COMPLAINT STATUS
# ============================================================

STATUS_SUBMITTED = "SUBMITTED"
STATUS_AI_ANALYSIS = "AI_ANALYSIS"
STATUS_ASSIGNED = "ASSIGNED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_RESOLVED = "RESOLVED"
STATUS_CLOSED = "CLOSED"
STATUS_REOPENED = "REOPENED"


# ============================================================
# EXPERIMENT / EVALUATION CONFIGURATION
# ============================================================

# Random seed used for reproducible experiments.
RANDOM_SEED = 42

# Dataset split ratios.
TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TEST_RATIO = 0.15

# Traditional baseline for comparison.
BASELINE_METHOD = "TF-IDF + Logistic Regression"

# Our final proposed semantic approach.
PROPOSED_METHOD = "TBD"


# ============================================================
# PAGINATION CONFIGURATION
# ============================================================

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100