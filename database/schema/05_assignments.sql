-- Assignments Table
-- Tracks assignment of complaints to department officers

CREATE TABLE IF NOT EXISTS assignments (
    assignment_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    assigned_to INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assigned_by INTEGER NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline TIMESTAMP,
    status VARCHAR(30) CHECK (status IN ('PENDING', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'REASSIGNED')) DEFAULT 'PENDING',
    notes TEXT,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_assignments_complaint_id ON assignments(complaint_id);
CREATE INDEX idx_assignments_assigned_to ON assignments(assigned_to);
CREATE INDEX idx_assignments_status ON assignments(status);
CREATE INDEX idx_assignments_assigned_at ON assignments(assigned_at DESC);

-- Create trigger to update updated_at
CREATE OR REPLACE FUNCTION update_assignments_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER assignments_updated_at_trigger
BEFORE UPDATE ON assignments
FOR EACH ROW
EXECUTE FUNCTION update_assignments_timestamp();
