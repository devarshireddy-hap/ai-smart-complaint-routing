-- Seed Data for Complaint Routing System
-- Initializes frozen roles, permissions, and departments

-- ============================================================================
-- INSERT ROLES
-- ============================================================================
INSERT INTO roles (role_name, description) VALUES
    ('ADMIN', 'System administrator with full access'),
    ('OFFICER', 'Department officer who handles complaints'),
    ('USER', 'Regular user who submits complaints')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- INSERT PERMISSIONS
-- ============================================================================
INSERT INTO permissions (permission_name, description, module) VALUES
    -- Complaint permissions
    ('complaint.create', 'Create new complaint', 'complaints'),
    ('complaint.read', 'View complaints', 'complaints'),
    ('complaint.update', 'Update complaint details', 'complaints'),
    ('complaint.delete', 'Delete complaint', 'complaints'),
    ('complaint.assign', 'Assign complaint to officer', 'complaints'),
    ('complaint.analyze', 'Run AI analysis on complaint', 'complaints'),
    ('complaint.resolve', 'Mark complaint as resolved', 'complaints'),
    ('complaint.reopen', 'Reopen a resolved complaint', 'complaints'),
    ('feedback.create', 'Submit complaint feedback', 'complaints'),
    
    -- User permissions
    ('user.read', 'View user information', 'users'),
    ('user.update', 'Update user information', 'users'),
    ('user.create', 'Create new user', 'users'),
    ('user.delete', 'Delete/deactivate user', 'users'),
    
    -- Department permissions
    ('department.read', 'View departments', 'departments'),
    ('department.manage', 'Manage department settings', 'departments'),
    ('category.manage', 'Create/update categories', 'departments'),
    
    -- Admin permissions
    ('admin.access', 'Access admin dashboard', 'admin'),
    ('admin.reports', 'View system reports', 'admin'),
    ('admin.audit', 'View audit logs', 'admin'),
    ('backup.manage', 'Manage backups and restores', 'admin'),
    
    -- RAG permissions
    ('rag.manage', 'Manage knowledge base documents', 'ai')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- ASSIGN PERMISSIONS TO ROLES
-- ============================================================================
-- USER role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id FROM roles r, permissions p
WHERE r.role_name = 'USER'
  AND p.permission_name IN (
    'complaint.create', 'complaint.read', 'complaint.reopen',
    'feedback.create', 'user.read', 'department.read'
  )
ON CONFLICT DO NOTHING;

-- OFFICER role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id FROM roles r, permissions p
WHERE r.role_name = 'OFFICER' 
  AND p.permission_name IN (
    'complaint.read', 'complaint.update', 'complaint.analyze', 
    'complaint.assign', 'complaint.resolve',
    'user.read', 'department.read', 'category.manage'
  )
ON CONFLICT DO NOTHING;

-- ADMIN role permissions (all permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id FROM roles r, permissions p
WHERE r.role_name = 'ADMIN'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- INSERT FROZEN DEPARTMENTS (5 Fixed)
-- ============================================================================
INSERT INTO departments (department_name, description, email, phone, is_active) VALUES
    ('TECHNICAL', 'Technical and IT-related issues', 'technical@institution.edu', '+1-XXX-XXX-1001', TRUE),
    ('FINANCE', 'Financial and billing-related issues', 'finance@institution.edu', '+1-XXX-XXX-1002', TRUE),
    ('ELECTRICAL', 'Electrical and power-related issues', 'electrical@institution.edu', '+1-XXX-XXX-1003', TRUE),
    ('PLUMBING', 'Plumbing and water-related issues', 'plumbing@institution.edu', '+1-XXX-XXX-1004', TRUE),
    ('SECURITY', 'Security and safety-related issues', 'security@institution.edu', '+1-XXX-XXX-1005', TRUE)
ON CONFLICT (department_name) DO NOTHING;

-- ============================================================================
-- INSERT SAMPLE CATEGORIES (Under each department)
-- ============================================================================
-- Technical Categories
INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Internet Connectivity', 'Network and internet issues', d.department_id, 4, TRUE
FROM departments d WHERE d.department_name = 'TECHNICAL'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Computer Hardware', 'PC, laptop, peripherals issues', d.department_id, 8, TRUE
FROM departments d WHERE d.department_name = 'TECHNICAL'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Software Support', 'Software installation, licensing issues', d.department_id, 8, TRUE
FROM departments d WHERE d.department_name = 'TECHNICAL'
ON CONFLICT DO NOTHING;

-- Finance Categories
INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Fee & Payment', 'Fee structure and payment issues', d.department_id, 24, TRUE
FROM departments d WHERE d.department_name = 'FINANCE'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Billing Issues', 'Incorrect billing or invoice disputes', d.department_id, 24, TRUE
FROM departments d WHERE d.department_name = 'FINANCE'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Refund Request', 'Refund or reimbursement requests', d.department_id, 48, TRUE
FROM departments d WHERE d.department_name = 'FINANCE'
ON CONFLICT DO NOTHING;

-- Electrical Categories
INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Power Outage', 'Power failure or outages', d.department_id, 2, TRUE
FROM departments d WHERE d.department_name = 'ELECTRICAL'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Electrical Damage', 'Faulty outlets, switches, or wiring', d.department_id, 4, TRUE
FROM departments d WHERE d.department_name = 'ELECTRICAL'
ON CONFLICT DO NOTHING;

-- Plumbing Categories
INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Water Leakage', 'Pipe leaks or water seepage', d.department_id, 4, TRUE
FROM departments d WHERE d.department_name = 'PLUMBING'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'No Water Supply', 'Water supply interruption', d.department_id, 2, TRUE
FROM departments d WHERE d.department_name = 'PLUMBING'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Blocked Drains', 'Drainage problems or blockages', d.department_id, 8, TRUE
FROM departments d WHERE d.department_name = 'PLUMBING'
ON CONFLICT DO NOTHING;

-- Security Categories
INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Theft/Loss', 'Missing items or theft report', d.department_id, 24, TRUE
FROM departments d WHERE d.department_name = 'SECURITY'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Safety Concern', 'Safety hazard or risk assessment', d.department_id, 4, TRUE
FROM departments d WHERE d.department_name = 'SECURITY'
ON CONFLICT DO NOTHING;

INSERT INTO categories (category_name, description, department_id, sla_hours, is_active)
SELECT 'Access Issue', 'Access card or entry problems', d.department_id, 8, TRUE
FROM departments d WHERE d.department_name = 'SECURITY'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Verification queries (uncomment to verify data)
-- ============================================================================
-- SELECT * FROM roles;
-- SELECT * FROM permissions;
-- SELECT * FROM departments;
-- SELECT COUNT(*) FROM categories;
-- SELECT c.category_name, d.department_name FROM categories c
-- JOIN departments d ON c.department_id = d.department_id
-- ORDER BY d.department_name;
