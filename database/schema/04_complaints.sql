-- Complaints Table
-- Stores all complaints submitted by users
-- Final status set: SUBMITTED, ASSIGNED, IN_PROGRESS, RESOLVED, REJECTED

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(category_id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(department_id) ON DELETE SET NULL,
    priority VARCHAR(20) CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')) DEFAULT 'MEDIUM',
    status VARCHAR(50) CHECK (status IN ('SUBMITTED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED')) DEFAULT 'SUBMITTED',
    urgency_score INTEGER DEFAULT 0, -- ML predicted urgency (0-100)
    location VARCHAR(255),
    attachment_urls TEXT[], -- Array of attachment URLs
    submission_mode VARCHAR(20) DEFAULT 'WEB', -- WEB, MOBILE, IN_PERSON
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of INTEGER REFERENCES complaints(complaint_id) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0, -- Confidence of AI routing (0-1)
    ai_suggested_department_id INTEGER REFERENCES departments(department_id),
    ai_suggested_priority VARCHAR(20),
    rag_relevant_docs TEXT[], -- Store IDs of relevant documents from RAG
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Create indexes for commonly filtered queries
CREATE INDEX idx_complaints_user_id ON complaints(user_id);
CREATE INDEX idx_complaints_status ON complaints(status);
CREATE INDEX idx_complaints_priority ON complaints(priority);
CREATE INDEX idx_complaints_department_id ON complaints(department_id);
CREATE INDEX idx_complaints_category_id ON complaints(category_id);
CREATE INDEX idx_complaints_created_at ON complaints(created_at DESC);
CREATE INDEX idx_complaints_is_duplicate ON complaints(is_duplicate);
CREATE INDEX idx_complaints_confidence_score ON complaints(confidence_score DESC);

-- Create trigger to update updated_at
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

-- Update foreign key constraint on departments if not already done
ALTER TABLE users 
ADD CONSTRAINT fk_users_department_id 
FOREIGN KEY (department_id) 
REFERENCES departments(department_id) 
ON DELETE SET NULL;
