# Entity-Relationship Diagram

This diagram represents the finalized PostgreSQL database schema for the AI
Smart Complaint Routing system. Department handling is represented via `department_id` and `status`, without a separate assignment table.

```mermaid
erDiagram
    USERS {
        int user_id PK
        varchar email UK
        varchar name
        varchar phone
        varchar user_type
        int department_id FK
        boolean is_active
        timestamp created_at
        timestamp updated_at
        timestamp last_login
        varchar google_id UK
        text profile_picture_url
    }

    ROLES {
        int role_id PK
        varchar role_name UK
        text description
        timestamp created_at
    }

    PERMISSIONS {
        int permission_id PK
        varchar permission_name UK
        text description
        varchar module
        timestamp created_at
    }

    ROLE_PERMISSIONS {
        int role_id PK, FK
        int permission_id PK, FK
        timestamp assigned_at
    }

    USER_ROLES {
        int user_id PK, FK
        int role_id PK, FK
        timestamp assigned_at
        int assigned_by FK
    }

    DEPARTMENTS {
        int department_id PK
        varchar department_name UK
        text description
        int head_id FK
        varchar email
        varchar phone
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    CATEGORIES {
        int category_id PK
        varchar category_name
        text description
        int department_id FK
        int sla_hours
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    COMPLAINTS {
        int complaint_id PK
        int user_id FK
        varchar title
        text description
        int category_id FK
        int department_id FK
        varchar priority
        varchar status
        int urgency_score
        varchar location
        text_array attachment_urls
        varchar submission_mode
        boolean is_duplicate
        int duplicate_of FK
        float confidence_score
        int ai_suggested_department_id FK
        text_array rag_relevant_docs
        timestamp created_at
        timestamp updated_at
        timestamp resolved_at
        timestamp closed_at
    }

    COMPLAINT_HISTORY {
        int history_id PK
        int complaint_id FK
        int changed_by FK
        varchar change_type
        jsonb old_values
        jsonb new_values
        varchar changed_field
        text change_description
        timestamp changed_at
        varchar ip_address
    }

    RESOLUTIONS {
        int resolution_id PK
        int complaint_id UK, FK
        int resolved_by FK
        text resolution_description
        varchar resolution_category
        text action_taken
        interval time_to_resolve
        boolean satisfaction_likely
        timestamp resolved_at
        timestamp updated_at
    }

    COMPLAINT_EMBEDDINGS {
        int embedding_id PK
        int complaint_id UK, FK
        vector embedding_vector
        varchar embedding_model
        timestamp created_at
        timestamp updated_at
    }

    KNOWLEDGE_DOCUMENT_CHUNKS {
        int chunk_id PK
        int document_id
        int department_id FK
        varchar title
        text chunk_text
        int chunk_index
        vector chunk_embedding
        varchar embedding_model
        jsonb metadata
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    AUDIT_LOGS {
        int log_id PK
        int user_id FK
        varchar action
        varchar resource_type
        int resource_id
        jsonb old_values
        jsonb new_values
        varchar status
        varchar ip_address
        text user_agent
        timestamp created_at
    }

    BACKUP_RECORDS {
        int backup_id PK
        varchar backup_name UK
        int created_by FK
        varchar backup_type
        text backup_location
        int size_mb
        varchar status
        timestamp created_at
        timestamp expires_at
    }

    ROLLBACK_RECORDS {
        int rollback_id PK
        int backup_id FK
        int initiated_by FK
        varchar status
        text reason
        timestamp created_at
        timestamp completed_at
    }

    FEEDBACK {
        int feedback_id PK
        int complaint_id FK
        int user_id FK
        int rating
        text comment
        boolean resolution_helpful
        timestamp created_at
    }

    USERS ||--o{ USER_ROLES : assigned
    ROLES ||--o{ USER_ROLES : contains
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : includes
    USERS ||--o{ USER_ROLES : assigns

    DEPARTMENTS ||--o{ USERS : employs
    USERS ||--o| DEPARTMENTS : heads
    DEPARTMENTS ||--o{ CATEGORIES : contains

    USERS ||--o{ COMPLAINTS : submits
    CATEGORIES ||--o{ COMPLAINTS : classifies
    DEPARTMENTS ||--o{ COMPLAINTS : receives
    DEPARTMENTS ||--o{ COMPLAINTS : suggested_for
    COMPLAINTS ||--o{ COMPLAINTS : duplicates

    COMPLAINTS ||--o{ COMPLAINT_HISTORY : tracks
    USERS ||--o{ COMPLAINT_HISTORY : changes
    COMPLAINTS ||--o| RESOLUTIONS : receives
    USERS ||--o{ RESOLUTIONS : resolves

    COMPLAINTS ||--o| COMPLAINT_EMBEDDINGS : generates
    DEPARTMENTS ||--o{ KNOWLEDGE_DOCUMENT_CHUNKS : owns

    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ BACKUP_RECORDS : creates
    BACKUP_RECORDS ||--o{ ROLLBACK_RECORDS : supports
    USERS ||--o{ ROLLBACK_RECORDS : initiates
    COMPLAINTS ||--o{ FEEDBACK : receives
    USERS ||--o{ FEEDBACK : submits
```

## Main Relationship Flow

```text
USER -> COMPLAINT -> ASSIGNMENT -> OFFICER
                  -> COMPLAINT_HISTORY
                  -> RESOLUTION
                  -> FEEDBACK
                  -> COMPLAINT_EMBEDDING

DEPARTMENT -> CATEGORY -> COMPLAINT
DEPARTMENT -> KNOWLEDGE_DOCUMENT_CHUNKS

USER -> ROLE -> PERMISSION
BACKUP_RECORD -> ROLLBACK_RECORD
```

The diagram can be rendered by GitHub and viewed in Mermaid-compatible tools
such as Mermaid Live Editor.

In this version, status changes like `ASSIGNED` and `IN_PROGRESS` are tracked on the complaint record itself.
`n> Manual workflow note: department and status are the active tracking fields; assignment is a dashboard action, not a database entity.`n