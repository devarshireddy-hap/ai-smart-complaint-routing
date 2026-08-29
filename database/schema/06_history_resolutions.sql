-- Complaint History Table
-- Tracks all changes to complaints for audit trail and history

CREATE TABLE IF NOT EXISTS complaint_history (
    history_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    changed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    change_type VARCHAR(50) NOT NULL, -- 'CREATED', 'UPDATED', 'STATUS_CHANGED', 'ASSIGNED', 'RESOLVED'
    old_values JSONB, -- Store old values as JSON for comparison
    new_values JSONB, -- Store new values as JSON
    changed_field VARCHAR(100), -- Which field was changed
    change_description TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- Create indexes
CREATE INDEX idx_complaint_history_complaint_id ON complaint_history(complaint_id);
CREATE INDEX idx_complaint_history_changed_by ON complaint_history(changed_by);
CREATE INDEX idx_complaint_history_changed_at ON complaint_history(changed_at DESC);
CREATE INDEX idx_complaint_history_change_type ON complaint_history(change_type);

-- Resolutions Table
-- Stores resolution information for complaints

CREATE TABLE IF NOT EXISTS resolutions (
    resolution_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL UNIQUE REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    resolved_by INTEGER NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    resolution_description TEXT NOT NULL,
    resolution_category VARCHAR(100), -- e.g., 'FIXED', 'DUPLICATE', 'INVALID', 'EXTERNAL'
    action_taken TEXT,
    time_to_resolve INTERVAL, -- Time from complaint creation to resolution
    satisfaction_likely BOOLEAN,
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_resolutions_complaint_id ON resolutions(complaint_id);
CREATE INDEX idx_resolutions_resolved_by ON resolutions(resolved_by);
CREATE INDEX idx_resolutions_resolved_at ON resolutions(resolved_at DESC);

-- Create trigger to update updated_at
CREATE OR REPLACE FUNCTION update_resolutions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER resolutions_updated_at_trigger
BEFORE UPDATE ON resolutions
FOR EACH ROW
EXECUTE FUNCTION update_resolutions_timestamp();
