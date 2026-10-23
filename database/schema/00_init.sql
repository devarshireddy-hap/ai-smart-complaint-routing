-- PostgreSQL 16 + pgvector schema reference for the current CampusCare models.
-- The Flask application creates this schema through SQLAlchemy db.create_all().
-- Keep this file aligned with backend/models.py; it is not a migration script.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE roles (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE permissions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE role_permissions (
    role_id VARCHAR(36) NOT NULL REFERENCES roles(id),
    permission_id VARCHAR(36) NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE departments (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE,
    description VARCHAR(240) NOT NULL
);

CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(256),
    google_subject VARCHAR(255) UNIQUE,
    user_type VARCHAR(20) NOT NULL DEFAULT 'STUDENT'
        CHECK (user_type IN ('STUDENT', 'FACULTY', 'WORKING_STAFF')),
    role_id VARCHAR(36) NOT NULL REFERENCES roles(id),
    department VARCHAR(30) REFERENCES departments(name),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE UNIQUE INDEX ix_users_email ON users(email);

CREATE TABLE categories (
    id VARCHAR(36) PRIMARY KEY,
    department VARCHAR(30) NOT NULL REFERENCES departments(name),
    name VARCHAR(80) NOT NULL,
    CONSTRAINT uq_category_department_name UNIQUE (department, name)
);
CREATE INDEX ix_categories_department ON categories(department);

CREATE TABLE complaints (
    id VARCHAR(36) PRIMARY KEY,
    reference VARCHAR(16) NOT NULL,
    reporter_id VARCHAR(36) NOT NULL REFERENCES users(id),
    title VARCHAR(160) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(160) NOT NULL,
    department VARCHAR(30) NOT NULL REFERENCES departments(name),
    category_id VARCHAR(36) NOT NULL REFERENCES categories(id),
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'
        CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
    status VARCHAR(24) NOT NULL DEFAULT 'SUBMITTED'
        CHECK (status IN ('SUBMITTED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'REOPENED')),
    assigned_to_id VARCHAR(36) REFERENCES users(id),
    suggested_resolution TEXT NOT NULL,
    resolution TEXT NOT NULL,
    ai_metadata JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE UNIQUE INDEX ix_complaints_reference ON complaints(reference);
CREATE INDEX ix_complaints_reporter_id ON complaints(reporter_id);
CREATE INDEX ix_complaints_department ON complaints(department);
CREATE INDEX ix_complaints_status ON complaints(status);
CREATE INDEX ix_complaints_created_at ON complaints(created_at);

CREATE TABLE complaint_history (
    id VARCHAR(36) PRIMARY KEY,
    complaint_id VARCHAR(36) NOT NULL REFERENCES complaints(id),
    actor_id VARCHAR(36) NOT NULL REFERENCES users(id),
    action VARCHAR(40) NOT NULL,
    before_state JSON,
    after_state JSON NOT NULL,
    note VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX ix_complaint_history_complaint_id ON complaint_history(complaint_id);

CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    actor_id VARCHAR(36) NOT NULL REFERENCES users(id),
    action VARCHAR(80) NOT NULL,
    resource_type VARCHAR(40) NOT NULL,
    resource_id VARCHAR(36),
    details JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX ix_audit_logs_created_at ON audit_logs(created_at);

CREATE TABLE feedback (
    id VARCHAR(36) PRIMARY KEY,
    complaint_id VARCHAR(36) NOT NULL REFERENCES complaints(id),
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_feedback_complaint_user UNIQUE (complaint_id, user_id)
);

CREATE TABLE backup_records (
    id VARCHAR(36) PRIMARY KEY,
    actor_id VARCHAR(36) NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    operation VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE rollback_records (
    id VARCHAR(36) PRIMARY KEY,
    complaint_id VARCHAR(36) NOT NULL REFERENCES complaints(id),
    actor_id VARCHAR(36) NOT NULL REFERENCES users(id),
    history_id VARCHAR(36) NOT NULL REFERENCES complaint_history(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE complaint_embeddings (
    complaint_id VARCHAR(36) PRIMARY KEY
        REFERENCES complaints(id) ON DELETE CASCADE,
    embedding VECTOR(384) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX ix_complaint_embeddings_hnsw
    ON complaint_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE TABLE knowledge_document_chunks (
    id VARCHAR(36) PRIMARY KEY,
    department VARCHAR(30) NOT NULL REFERENCES departments(name),
    source VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX ix_knowledge_document_chunks_department
    ON knowledge_document_chunks(department);
CREATE INDEX ix_knowledge_chunks_hnsw
    ON knowledge_document_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE historical_complaints (
    id VARCHAR(36) PRIMARY KEY,
    source_id INTEGER NOT NULL UNIQUE,
    complaint_text TEXT NOT NULL,
    department VARCHAR(30) NOT NULL REFERENCES departments(name),
    category_id VARCHAR(36) NOT NULL REFERENCES categories(id),
    priority VARCHAR(20) NOT NULL,
    resolution TEXT NOT NULL,
    embedding VECTOR(384)
);
CREATE INDEX ix_historical_complaints_department
    ON historical_complaints(department);
CREATE INDEX ix_historical_complaints_hnsw
    ON historical_complaints USING hnsw (embedding vector_cosine_ops);
