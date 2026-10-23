#============================================================
# API CONFIGURATION
# ============================================================

API_PREFIX = "/api/v1"
API_VERSION = "v1"
API_CONTENT_TYPE = "application/json"
API_PROTOCOL = "HTTPS"


# ============================================================
# PAGINATION CONFIGURATION
# ============================================================

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ============================================================
# USER ROLES
# ============================================================

ROLE_STUDENT = "STUDENT"
ROLE_FACULTY = "FACULTY"
ROLE_WORKING_STAFF = "WORKING_STAFF"
ROLE_ADMIN = "ADMIN"


# ============================================================
# COMPLAINT DEPARTMENTS
# ============================================================

DEPARTMENT_TECHNICAL = "TECHNICAL"
DEPARTMENT_FINANCE = "FINANCE"
DEPARTMENT_ELECTRICAL = "ELECTRICAL"
DEPARTMENT_PLUMBING = "PLUMBING"
DEPARTMENT_SECURITY = "SECURITY"


# ============================================================
# COMPLAINT STATUS
# ============================================================

STATUS_SUBMITTED = "SUBMITTED"
STATUS_ASSIGNED = "ASSIGNED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_RESOLVED = "RESOLVED"
STATUS_REJECTED = "REJECTED"


# ============================================================
# COMPLAINT PRIORITY LEVELS
# ============================================================

PRIORITY_LOW = "LOW"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_HIGH = "HIGH"
PRIORITY_URGENT = "URGENT"


# ============================================================
# AI MODEL CONFIGURATION
# ============================================================

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

EMBEDDING_DIMENSION = 384

CLASSIFIER_MODEL_NAME = "TBD"

LLM_MODEL_NAME = "TBD"

MODEL_VERSION = "v1.0"

RANDOM_SEED = 42


# ============================================================
# VECTOR SEARCH CONFIGURATION
# ============================================================

VECTOR_EXTENSION = "vector"

SIMILARITY_METRIC = "cosine"

RAG_TOP_K = 5

DUPLICATE_TOP_K = 5

DUPLICATE_SIMILARITY_THRESHOLD = None

# ============================================================
# AI FEATURE FLAGS
# ============================================================

ENABLE_AI_ROUTING = True
ENABLE_DUPLICATE_DETECTION = True
ENABLE_RAG = True
ENABLE_AI_FEEDBACK = True
ENABLE_AI_EXPLANATION = True
ENABLE_LLM = True
USE_LLM_FALLBACK = True


# ============================================================
# EXPERIMENT / EVALUATION CONFIGURATION
# ============================================================

TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TEST_RATIO = 0.15

BASELINE_METHOD = "TF-IDF + Logistic Regression"

PROPOSED_METHOD = "TBD"


# ============================================================
# OPTIONAL SEVERITY LEVELS
# ============================================================

SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"