-- CORRECTED COMPLAINTS TABLE
-- Added proper status lifecycle constraints
-- Status values: OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED
-- Special case: REOPENED when resolved complaint gets new issue

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(category_id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(department_id) ON DELETE SET NULL,
    
    -- Priority must be one of: LOW, MEDIUM, HIGH, URGENT
    priority VARCHAR(20) CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')) DEFAULT 'MEDIUM',
    
    -- Status lifecycle: OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED (or REOPENED)
    status VARCHAR(50) CHECK (status IN ('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'REOPENED')) DEFAULT 'OPEN',
    
    -- AI confidence and analysis
    urgency_score INTEGER DEFAULT 0 CHECK (urgency_score >= 0 AND urgency_score <= 100),
    location VARCHAR(255),
    attachment_urls TEXT[],
    submission_mode VARCHAR(20) DEFAULT 'WEB' CHECK (submission_mode IN ('WEB', 'MOBILE', 'IN_PERSON')),
    
    -- Duplicate detection
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of INTEGER REFERENCES complaints(complaint_id) ON DELETE SET NULL,
    
    -- AI routing confidence
    confidence_score FLOAT DEFAULT 0 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    ai_suggested_department_id INTEGER REFERENCES departments(department_id) ON DELETE SET NULL,
    ai_suggested_priority VARCHAR(20),
    
    -- RAG related
    rag_relevant_docs TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX idx_complaints_user_id ON complaints(user_id);
CREATE INDEX idx_complaints_status ON complaints(status);
CREATE INDEX idx_complaints_priority ON complaints(priority);
CREATE INDEX idx_complaints_department_id ON complaints(department_id);
CREATE INDEX idx_complaints_category_id ON complaints(category_id);
CREATE INDEX idx_complaints_created_at ON complaints(created_at DESC);
CREATE INDEX idx_complaints_is_duplicate ON complaints(is_duplicate);
CREATE INDEX idx_complaints_confidence_score ON complaints(confidence_score DESC);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_complaints_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER complaints_updated_at_trigger
BEFORE UPDATE ON complaints
FOR EACH ROW
EXECUTE FUNCTION update_complaints_timestamp();

-- Add foreign key constraint for user's department (if not already there)
ALTER TABLE users 
ADD CONSTRAINT fk_users_department_id 
FOREIGN KEY (department_id) 
REFERENCES departments(department_id) 
ON DELETE SET NULL;
