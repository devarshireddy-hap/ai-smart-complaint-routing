-- Complaint History Table
-- Tracks all changes to complaints for audit trail and status history

CREATE TABLE IF NOT EXISTS complaint_history (
    history_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    changed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    change_type VARCHAR(50) NOT NULL, -- 'SUBMITTED', 'UPDATED', 'STATUS_CHANGED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED'
    old_values JSONB,
    new_values JSONB,
    changed_field VARCHAR(100),
    change_description TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- Create indexes
CREATE INDEX idx_complaint_history_complaint_id ON complaint_history(complaint_id);
CREATE INDEX idx_complaint_history_changed_by ON complaint_history(changed_by);
CREATE INDEX idx_complaint_history_changed_at ON complaint_history(changed_at DESC);
CREATE INDEX idx_complaint_history_change_type ON complaint_history(change_type);
