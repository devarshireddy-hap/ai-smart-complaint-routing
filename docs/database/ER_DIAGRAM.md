# CampusCare Entity-Relationship Diagram

This diagram reflects the current application models in
[`backend/models.py`](../../backend/models.py), not the legacy integer-ID schema
on the separate GitHub `database` branch.

```mermaid
erDiagram
    ROLES ||--o{ USERS : assigned
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : included
    DEPARTMENTS ||--o{ USERS : assigned
    DEPARTMENTS ||--o{ CATEGORIES : contains
    DEPARTMENTS ||--o{ COMPLAINTS : routes
    DEPARTMENTS ||--o{ KNOWLEDGE_DOCUMENT_CHUNKS : informs
    DEPARTMENTS ||--o{ HISTORICAL_COMPLAINTS : classifies
    USERS ||--o{ COMPLAINTS : reports
    USERS o|--o{ COMPLAINTS : assigned_to
    CATEGORIES ||--o{ COMPLAINTS : categorizes
    CATEGORIES ||--o{ HISTORICAL_COMPLAINTS : categorizes
    COMPLAINTS ||--o{ COMPLAINT_HISTORY : tracks
    USERS ||--o{ COMPLAINT_HISTORY : acts
    COMPLAINTS ||--o| COMPLAINT_EMBEDDINGS : embeds
    COMPLAINTS ||--o{ FEEDBACK : receives
    USERS ||--o{ FEEDBACK : submits
    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ BACKUP_RECORDS : creates
    COMPLAINTS ||--o{ ROLLBACK_RECORDS : rolled_back
    USERS ||--o{ ROLLBACK_RECORDS : initiates
    COMPLAINT_HISTORY ||--o{ ROLLBACK_RECORDS : references

    ROLES {
        string id PK
        string name UK
    }
    PERMISSIONS {
        string id PK
        string name UK
    }
    ROLE_PERMISSIONS {
        string role_id PK,FK
        string permission_id PK,FK
    }
    USERS {
        string id PK
        string email UK
        string role_id FK
        string department FK
        string user_type
        boolean is_active
    }
    DEPARTMENTS {
        string id PK
        string name UK
        string description
    }
    CATEGORIES {
        string id PK
        string department FK
        string name
    }
    COMPLAINTS {
        string id PK
        string reference UK
        string reporter_id FK
        string assigned_to_id FK
        string department FK
        string category_id FK
        string status
        string priority
        json ai_metadata
    }
    COMPLAINT_HISTORY {
        string id PK
        string complaint_id FK
        string actor_id FK
        json before_state
        json after_state
    }
    COMPLAINT_EMBEDDINGS {
        string complaint_id PK,FK
        vector embedding
    }
    KNOWLEDGE_DOCUMENT_CHUNKS {
        string id PK
        string department FK
        string source
        vector embedding
    }
    HISTORICAL_COMPLAINTS {
        string id PK
        int source_id UK
        string department FK
        string category_id FK
        vector embedding
    }
    AUDIT_LOGS {
        string id PK
        string actor_id FK
        string action
        string resource_id
    }
    FEEDBACK {
        string id PK
        string complaint_id FK
        string user_id FK
        int rating
    }
    BACKUP_RECORDS {
        string id PK
        string actor_id FK
        string filename
    }
    ROLLBACK_RECORDS {
        string id PK
        string complaint_id FK
        string actor_id FK
        string history_id FK
    }
```
