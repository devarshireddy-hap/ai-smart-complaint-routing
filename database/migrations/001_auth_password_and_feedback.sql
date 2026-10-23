-- Apply to an existing database created before the application integration.
-- Safe to re-run; fresh databases also receive these values from the seed file.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_hash VARCHAR(256);

INSERT INTO permissions (permission_name, description, module) VALUES
    ('complaint.reopen', 'Reopen a resolved complaint', 'complaints'),
    ('feedback.create', 'Submit complaint feedback', 'complaints')
ON CONFLICT (permission_name) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles AS r
JOIN permissions AS p
  ON (r.role_name = 'CITIZEN' AND p.permission_name IN ('complaint.reopen', 'feedback.create'))
  OR r.role_name = 'ADMIN'
ON CONFLICT DO NOTHING;
