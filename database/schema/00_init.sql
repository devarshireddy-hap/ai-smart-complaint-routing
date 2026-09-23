-- Database Initialization Script
-- Creates all tables, extensions, functions, and triggers for the complaint routing system
-- Tech Stack: PostgreSQL 15+ with pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;

-- ============================================================================
-- 1. USERS TABLE
-- ============================================================================
-- Core user information with soft-delete support
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    user_type VARCHAR(50) NOT NULL CHECK (user_type IN ('STUDENT', 'FACULTY', 'WORKING_STAFF')),
    department_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    google_id VARCHAR(255) UNIQUE,
    profile_picture_url TEXT
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_user_type ON users(user_type);
CREATE INDEX idx_users_active ON users(is_active);

-- ============================================================================
-- 2. ROLES & PERMISSIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permissions (
    permission_id SERIAL PRIMARY KEY,
    permission_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    module VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(permission_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER REFERENCES users(user_id),
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);

-- ============================================================================
-- 3. DEPARTMENTS & CATEGORIES
-- ============================================================================
-- Departments are FROZEN (immutable set of 5)
CREATE TABLE IF NOT EXISTS departments (
    department_id SERIAL PRIMARY KEY,
    department_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    head_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_departments_name ON departments(department_name);
CREATE INDEX idx_departments_active ON departments(is_active);

-- Categories can be managed under departments
CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    description TEXT,
    department_id INTEGER NOT NULL REFERENCES departments(department_id) ON DELETE CASCADE,
    sla_hours INTEGER DEFAULT 24,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_name, department_id)
);

CREATE INDEX idx_categories_department_id ON categories(department_id);
CREATE INDEX idx_categories_active ON categories(is_active);

-- Add department foreign key to users
ALTER TABLE users ADD CONSTRAINT fk_users_department_id 
FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE SET NULL;

-- ============================================================================
-- 4. COMPLAINTS TABLE
-- ============================================================================
-- Main complaints table with AI routing support
-- Complaint assignment is managed manually in the dashboard through the complaint status and department fields.
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(category_id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(department_id) ON DELETE SET NULL,
    priority VARCHAR(20) CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')) DEFAULT 'MEDIUM',
    status VARCHAR(50) CHECK (status IN ('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'REOPENED')) DEFAULT 'OPEN',
    urgency_score INTEGER DEFAULT 0 CHECK (urgency_score >= 0 AND urgency_score <= 100),
    location VARCHAR(255),
    attachment_urls TEXT[],
    submission_mode VARCHAR(20) DEFAULT 'WEB' CHECK (submission_mode IN ('WEB', 'MOBILE', 'IN_PERSON')),
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of INTEGER REFERENCES complaints(complaint_id) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    ai_suggested_department_id INTEGER REFERENCES departments(department_id) ON DELETE SET NULL,
    ai_suggested_priority VARCHAR(20),
    rag_relevant_docs TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE INDEX idx_complaints_user_id ON complaints(user_id);
CREATE INDEX idx_complaints_status ON complaints(status);
CREATE INDEX idx_complaints_priority ON complaints(priority);
CREATE INDEX idx_complaints_department_id ON complaints(department_id);
CREATE INDEX idx_complaints_created_at ON complaints(created_at DESC);

-- ============================================================================
-- 5. COMPLAINT HISTORY & RESOLUTIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS complaint_history (
    history_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    changed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    change_type VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_field VARCHAR(100),
    change_description TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

CREATE INDEX idx_complaint_history_complaint_id ON complaint_history(complaint_id);
CREATE INDEX idx_complaint_history_changed_at ON complaint_history(changed_at DESC);

CREATE TABLE IF NOT EXISTS resolutions (
    resolution_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL UNIQUE REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    resolved_by INTEGER NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    resolution_description TEXT NOT NULL,
    resolution_category VARCHAR(100),
    action_taken TEXT,
    time_to_resolve INTERVAL,
    satisfaction_likely BOOLEAN,
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_resolutions_complaint_id ON resolutions(complaint_id);
CREATE INDEX idx_resolutions_resolved_at ON resolutions(resolved_at DESC);

-- ============================================================================
-- 6. EMBEDDINGS & VECTOR SEARCH
-- ============================================================================
CREATE TABLE IF NOT EXISTS complaint_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL UNIQUE REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    embedding_vector vector(384),
    embedding_model VARCHAR(100) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_complaint_embeddings_vector ON complaint_embeddings 
USING hnsw (embedding_vector vector_cosine_ops);

-- ============================================================================
-- 7. KNOWLEDGE BASE (NEW - for RAG)
-- ============================================================================
CREATE TABLE IF NOT EXISTS knowledge_document_chunks (
    chunk_id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(department_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER,
    chunk_embedding vector(384),
    embedding_model VARCHAR(100) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    metadata JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_chunks_department_id ON knowledge_document_chunks(department_id);
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_document_chunks 
USING hnsw (chunk_embedding vector_cosine_ops);

-- ============================================================================
-- 8. AUDIT LOGS
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    status VARCHAR(20),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- ============================================================================
-- 9. BACKUP & ROLLBACK RECORDS
-- ============================================================================
CREATE TABLE IF NOT EXISTS backup_records (
    backup_id SERIAL PRIMARY KEY,
    backup_name VARCHAR(255) UNIQUE NOT NULL,
    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    backup_type VARCHAR(50), -- FULL, INCREMENTAL, etc.
    backup_location TEXT,
    size_mb INTEGER,
    status VARCHAR(20), -- PENDING, COMPLETED, FAILED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rollback_records (
    rollback_id SERIAL PRIMARY KEY,
    backup_id INTEGER REFERENCES backup_records(backup_id) ON DELETE SET NULL,
    initiated_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    status VARCHAR(20), -- PENDING, IN_PROGRESS, COMPLETED, FAILED
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- ============================================================================
-- 10. FEEDBACK
-- ============================================================================
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    resolution_helpful BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_complaint_id ON feedback(complaint_id);

-- ============================================================================
-- TRIGGERS FOR TIMESTAMP MANAGEMENT
-- ============================================================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at_trigger BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER departments_updated_at_trigger BEFORE UPDATE ON departments FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER categories_updated_at_trigger BEFORE UPDATE ON categories FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER complaints_updated_at_trigger BEFORE UPDATE ON complaints FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER resolutions_updated_at_trigger BEFORE UPDATE ON resolutions FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER complaint_embeddings_updated_at_trigger BEFORE UPDATE ON complaint_embeddings FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER knowledge_chunks_updated_at_trigger BEFORE UPDATE ON knowledge_document_chunks FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================================================
-- CONSTRAINTS & POLICIES
-- ============================================================================
-- Prevent user deletion
CREATE OR REPLACE FUNCTION prevent_user_deletion()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Direct user deletion not allowed. Use is_active = FALSE.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_user_delete_trigger BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION prevent_user_deletion();

-- Prevent department deletion (frozen set)
CREATE OR REPLACE FUNCTION prevent_department_deletion()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Department deletion not allowed. Departments are frozen.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_dept_delete_trigger BEFORE DELETE ON departments FOR EACH ROW EXECUTE FUNCTION prevent_department_deletion();
`n-- Manual assignment workflow: the dashboard updates complaint status and department; no separate assignment table is used.`n`n-- Complaints keep the active work state in status and department_id for dashboard-driven routing and staff updates.`n`n-- Status history is preserved in complaint_history to record manual updates without an assignments table.`n