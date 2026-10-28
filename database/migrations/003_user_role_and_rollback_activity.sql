-- Rename the public Citizen role to User while preserving existing assignments.
DO $$
DECLARE
    legacy_role_id INTEGER;
    user_role_id INTEGER;
BEGIN
    SELECT role_id INTO legacy_role_id
    FROM roles
    WHERE role_name = 'CITIZEN';

    SELECT role_id INTO user_role_id
    FROM roles
    WHERE role_name = 'USER';

    IF legacy_role_id IS NOT NULL AND user_role_id IS NULL THEN
        UPDATE roles
        SET role_name = 'USER',
            description = 'Regular user who submits complaints'
        WHERE role_id = legacy_role_id;
    ELSIF legacy_role_id IS NOT NULL THEN
        INSERT INTO user_roles (user_id, role_id, assigned_at, assigned_by)
        SELECT user_id, user_role_id, assigned_at, assigned_by
        FROM user_roles
        WHERE role_id = legacy_role_id
        ON CONFLICT (user_id, role_id) DO NOTHING;

        INSERT INTO role_permissions (role_id, permission_id, assigned_at)
        SELECT user_role_id, permission_id, assigned_at
        FROM role_permissions
        WHERE role_id = legacy_role_id
        ON CONFLICT (role_id, permission_id) DO NOTHING;

        DELETE FROM user_roles WHERE role_id = legacy_role_id;
        DELETE FROM role_permissions WHERE role_id = legacy_role_id;
        DELETE FROM roles WHERE role_id = legacy_role_id;
    END IF;
END;
$$;

ALTER TABLE rollback_records
    ADD COLUMN IF NOT EXISTS reversed_history_id INTEGER
        REFERENCES complaint_history(history_id) ON DELETE SET NULL;

ALTER TABLE rollback_records
    ADD COLUMN IF NOT EXISTS rollback_history_id INTEGER
        REFERENCES complaint_history(history_id) ON DELETE SET NULL;
