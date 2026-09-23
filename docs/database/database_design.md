# Database Design & Implementation

## Overview

The AI Smart Complaint Routing system uses PostgreSQL 15+ with pgvector extension for semantic vector search. The database schema implements a comprehensive role-based access control system with full audit capabilities. Complaint status is managed manually from the dashboard instead of a separate assignment table. Complaint status is managed manually via the dashboard rather than through a dedicated assignment table.

## Tech Stack

- **Database**: PostgreSQL 15+
- **Vector Search**: pgvector (384-dimensional vectors)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **ORM**: SQLAlchemy (Python)
- **Schema Management**: Alembic migrations
- **Caching** (optional): Redis

## Core Architecture

### 1. User Management

#### Users Table
Stores all users in the system with soft-delete support to preserve audit trails.

```sql
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    user_type VARCHAR(50) -- STUDENT, FACULTY, WORKING_STAFF
    is_active BOOLEAN DEFAULT TRUE,
    ...
);
```

**Key Features:**
- Soft delete: Use `is_active = FALSE` instead of physical deletion
- Google OAuth integration via `google_id`
- Last login tracking
- Profile picture URL storage

### 2. Role-Based Access Control (RBAC)

Three-tier permission system:

```
Users → Roles → Permissions
  ↓        ↓          ↓
 user_id role_id   permission_id
```

**Roles:**
- `ADMIN` - Full system access
- `OFFICER` - Department staff, can handle complaints
- `CITIZEN` - Users submitting complaints

**Permission Categories:**
- Complaint management (CRUD, assign, analyze, resolve)
- User management
- Department/category management
- Admin functions (backups, audit logs)
- RAG/AI management

### 3. Departments & Categories

#### Frozen Departments (Immutable Set of 5)
```
1. TECHNICAL   - IT and technical issues
2. FINANCE     - Financial and billing issues
3. ELECTRICAL  - Electrical and power issues
4. PLUMBING    - Water and plumbing issues
5. SECURITY    - Security and safety issues
```

**Critical Constraint:** Departments cannot be created or deleted. Admins can only manage categories.

#### Categories (Dynamic, Under Departments)
Admins can create/manage categories under each department:
- TECHNICAL: Internet Connectivity, Computer Hardware, Software Support
- FINANCE: Fee & Payment, Billing Issues, Refund Request
- ELECTRICAL: Power Outage, Electrical Damage
- PLUMBING: Water Leakage, No Water Supply, Blocked Drains
- SECURITY: Theft/Loss, Safety Concern, Access Issue

### 4. Complaint Management

#### Main Complaint Workflow

The complaint lifecycle is maintained manually through the dashboard; status changes such as ASSIGNED and IN_PROGRESS are stored directly on the complaint record.

```
┌──────────────────────────────────────────────────┐
│           COMPLAINT STATUS WORKFLOW              │
├──────────────────────────────────────────────────┤
│                                                  │
│  OPEN                                            │
│    ↓ (AI Analysis)                              │
│  OPEN                                            │
│    ↓ (Manual department handling)               │
│  ASSIGNED     [Handled manually in dashboard]    │
│    ↓ (Work in progress)                         │
│  IN_PROGRESS  [Officer investigating]            │
│    ↓ (Solution provided)                        │
│  RESOLVED     [Fix applied, awaiting feedback]   │
│    ├→ CLOSED  [User satisfied, done]             │
│    └→ REOPENED [User not satisfied]              │
│         ↓ (Back to investigation)               │
│      IN_PROGRESS                                 │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### Complaint Table Fields

```sql
complaint_id          SERIAL PRIMARY KEY
user_id              INTEGER (who submitted)
title                VARCHAR(255)
description          TEXT
category_id          INTEGER (selected/AI-suggested)
department_id        INTEGER (selected/AI-suggested)
priority             ENUM(LOW, MEDIUM, HIGH, URGENT)
status               ENUM(OPEN, IN_PROGRESS, RESOLVED, CLOSED, REOPENED)
urgency_score        INTEGER (0-100, AI-calculated)
confidence_score     FLOAT (0-1, AI confidence)
is_duplicate         BOOLEAN
duplicate_of         INTEGER (reference to original complaint)
location             VARCHAR(255)
attachment_urls      TEXT[] (array of file URLs)
submission_mode      ENUM(WEB, MOBILE, IN_PERSON)
rag_relevant_docs    TEXT[] (relevant knowledge chunks)
created_at           TIMESTAMP
updated_at           TIMESTAMP
resolved_at          TIMESTAMP
closed_at            TIMESTAMP
```

### 5. AI & Vector Search

#### Complaint Embeddings Table

Stores 384-dimensional embeddings for each complaint:

```sql
CREATE TABLE complaint_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    complaint_id INTEGER UNIQUE,
    embedding_vector vector(384),  -- pgvector column
    embedding_model VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_complaint_embeddings_vector ON complaint_embeddings
USING hnsw (embedding_vector vector_cosine_ops);
```

**Semantic Similarity Search:**

```sql
-- Find 5 most similar complaints
SELECT complaint_id, similarity FROM complaint_embeddings
WHERE complaint_id != NEW.complaint_id
ORDER BY embedding_vector <-> NEW.embedding_vector
LIMIT 5;
```

#### Knowledge Base (RAG)

Stores documents/chunks for Retrieval-Augmented Generation:

```sql
CREATE TABLE knowledge_document_chunks (
    chunk_id SERIAL PRIMARY KEY,
    document_id INTEGER,
    department_id INTEGER,
    title VARCHAR(255),
    chunk_text TEXT,           -- Actual content
    chunk_index INTEGER,       -- Order in document
    chunk_embedding vector(384), -- Vector for search
    metadata JSONB,            -- Tags, source, etc.
    is_active BOOLEAN
);

-- Vector similarity search on knowledge base
SELECT chunk_id, similarity FROM knowledge_document_chunks
WHERE department_id = target_department
ORDER BY chunk_embedding <-> query_embedding
LIMIT 10;
```

### 6. Audit & Compliance

#### Complaint History
Tracks every change to a complaint:

```sql
CREATE TABLE complaint_history (
    history_id SERIAL PRIMARY KEY,
    complaint_id INTEGER,
    changed_by INTEGER,         -- User who made change
    change_type VARCHAR(50),    -- CREATED, UPDATED, ASSIGNED, RESOLVED
    old_values JSONB,          -- Previous values
    new_values JSONB,          -- New values
    changed_field VARCHAR(100),
    changed_at TIMESTAMP,
    ip_address VARCHAR(45)
);
```

#### Audit Logs
System-wide action logging:

```sql
CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100),       -- CREATE, UPDATE, DELETE, LOGIN, etc.
    resource_type VARCHAR(50), -- complaint, user, department, etc.
    resource_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    status VARCHAR(20),        -- SUCCESS, FAILED
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP
);
```

#### Resolutions
Tracks how complaints were resolved (1:1 relationship):

```sql
CREATE TABLE resolutions (
    resolution_id SERIAL PRIMARY KEY,
    complaint_id INTEGER UNIQUE,  -- One per complaint
    resolved_by INTEGER,          -- Officer who resolved
    resolution_description TEXT,  -- What was done
    resolution_category VARCHAR(100), -- FIXED, DUPLICATE, INVALID
    time_to_resolve INTERVAL,     -- How long it took
    satisfaction_likely BOOLEAN,  -- AI prediction
    resolved_at TIMESTAMP
);
```

### 7. Backup & Disaster Recovery

#### Backup Records
```sql
CREATE TABLE backup_records (
    backup_id SERIAL PRIMARY KEY,
    backup_name VARCHAR(255),
    backup_type VARCHAR(50),      -- FULL, INCREMENTAL
    backup_location TEXT,         -- File path or S3 URL
    size_mb INTEGER,
    status VARCHAR(20),           -- COMPLETED, FAILED
    created_at TIMESTAMP,
    expires_at TIMESTAMP          -- Retention policy
);
```

#### Rollback Records
```sql
CREATE TABLE rollback_records (
    rollback_id SERIAL PRIMARY KEY,
    backup_id INTEGER,
    initiated_by INTEGER,
    status VARCHAR(20),           -- PENDING, IN_PROGRESS, COMPLETED
    reason TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

## Important Constraints & Rules

### 1. User Deletion Policy
❌ **NOT ALLOWED:** Physical deletion of users
✅ **REQUIRED:** Soft delete using `is_active = FALSE`

**Why:**
- Preserves audit trail
- Maintains referential integrity
- Historical complaints remain linked to creators
- Compliant with data protection requirements

**Implementation:**
```sql
CREATE OR REPLACE FUNCTION prevent_user_deletion()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Direct user deletion not allowed.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_user_delete_trigger
BEFORE DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION prevent_user_deletion();
```

### 2. Department Immutability
❌ **NOT ALLOWED:** Creating or deleting departments
✅ **ALLOWED:** Activating/deactivating departments

**Frozen Departments:**
- TECHNICAL
- FINANCE
- ELECTRICAL
- PLUMBING
- SECURITY

### 3. AI Routing Semantics
❌ **NOT ALLOWED:**
```python
if "water" in complaint_text:
    department = "PLUMBING"
```

✅ **REQUIRED:**
```
Complaint → Embedding → Vector Similarity Search → RAG → LLM → Department
```

### 4. Complaint Resolution
- **One active resolution per complaint** (UNIQUE constraint)
- Previous resolutions stored in complaint_history
- Resolution category: FIXED, DUPLICATE, INVALID, etc.
- Time to resolve tracked for metrics

### 5. Complaint Duplication
- Automatic duplicate detection via embedding similarity
- `is_duplicate` flag set to TRUE
- `duplicate_of` field references original complaint
- Duplicates linked in audit trail

## Database Indexes (Performance)

### Primary Indexes
```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_active ON users(is_active);

-- Complaint queries
CREATE INDEX idx_complaints_user_id ON complaints(user_id);
CREATE INDEX idx_complaints_status ON complaints(status);
CREATE INDEX idx_complaints_department_id ON complaints(department_id);
CREATE INDEX idx_complaints_created_at ON complaints(created_at DESC);

-- Vector similarity search
CREATE INDEX idx_complaint_embeddings_vector ON complaint_embeddings
USING hnsw (embedding_vector vector_cosine_ops);

CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_document_chunks
USING hnsw (chunk_embedding vector_cosine_ops);

-- Audit queries
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
```

## Data Dictionary

### Enums

**user_type:**
- STUDENT
- FACULTY
- WORKING_STAFF

**role_name:**
- ADMIN
- OFFICER
- CITIZEN

**priority:**
- LOW
- MEDIUM
- HIGH
- URGENT

**status (complaints):**
- OPEN
- ASSIGNED
- IN_PROGRESS
- RESOLVED
- CLOSED
- REOPENED

The `ASSIGNED` value represents manual department handling from the dashboard.

**change_type (complaint_history):**
- CREATED
- UPDATED
- STATUS_CHANGED
- ASSIGNED
- RESOLVED
- REOPENED

**resolution_category:**
- FIXED
- DUPLICATE
- INVALID
- EXTERNAL
- ESCALATED

## Relationships Diagram

```
                    USERS
                      |
         ┌────────────┼────────────┐
         |            |            |
      ROLES      DEPARTMENTS   COMPLAINTS
         |            |            |
         |            |      ┌─────┼─────┐
    PERMISSIONS    CATEGORIES |     |     |
         |                    |     |     |
    ROLE_PERMS                     |     |
                                   |     |
                      COMPLAINT_EMBEDDINGS
                      
                      COMPLAINT_HISTORY
                      RESOLUTIONS
                      AUDIT_LOGS
                      FEEDBACK
```

## Setup Instructions

### 1. Create Database
```bash
createdb complaint_routing
```

### 2. Run Initial Schema
```bash
psql complaint_routing < database/schema/00_init.sql
```

### 3. Seed Initial Data
```bash
psql complaint_routing < database/seeds/01_init_data.sql
```

### 4. Enable pgvector
```bash
psql complaint_routing -c "CREATE EXTENSION IF NOT EXISTS pgvector;"
```

### 5. Run Migrations
```bash
python -m alembic upgrade head
```

## Connection String

**Format:**
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Example:**
```
postgresql://postgres:password@localhost:5432/complaint_routing
```

## Performance Considerations

1. **Vector Indexes**: Use HNSW (Hierarchical Navigable Small World) for fast similarity search
2. **Partitioning** (optional): For large complaint volumes, partition by date
3. **Query Optimization**: Use EXPLAIN ANALYZE for complex queries
4. **Caching**: Cache frequent queries with Redis
5. **Bulk Operations**: Use COPY for large data imports

## Security

- All changes logged to audit_logs
- User actions tracked with IP addresses
- Role-based permission checks at application level
- SQL injection prevention via parameterized queries (SQLAlchemy)
- Encrypted Google OAuth tokens
- Environment variables for sensitive configuration

## Compliance & Standards

- ACID transactions ensure data integrity
- Soft delete preserves audit trails
- Complete audit logging for compliance
- Backup/restore for disaster recovery
- Rollback capability for incident response

## Next Steps

1. Deploy to PostgreSQL 15+
2. Configure pgvector extension
3. Run schema initialization
4. Seed initial data
5. Connect via SQLAlchemy ORM in Flask backend
6. Implement RAG pipeline for knowledge base
7. Set up vector embeddings service
8. Configure backup schedule
