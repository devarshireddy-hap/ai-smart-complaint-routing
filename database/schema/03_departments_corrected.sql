-- CORRECTED DEPARTMENTS TABLE
-- Fixed: Departments are READ-ONLY (frozen set of 5)
-- Admins can manage categories under departments, but NOT create/delete departments

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

-- FROZEN DEPARTMENTS (must be seeded during initialization)
-- TECHNICAL, FINANCE, ELECTRICAL, PLUMBING, SECURITY
-- These 5 departments are immutable - prevent creation and deletion

CREATE OR REPLACE FUNCTION prevent_department_deletion()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Department deletion is not allowed. Departments are frozen. Use is_active = FALSE to deactivate.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_dept_delete_trigger
BEFORE DELETE ON departments
FOR EACH ROW
EXECUTE FUNCTION prevent_department_deletion();

-- Create index
CREATE INDEX idx_departments_name ON departments(department_name);
CREATE INDEX idx_departments_head_id ON departments(head_id);
CREATE INDEX idx_departments_active ON departments(is_active);

-- Create trigger to update updated_at
CREATE OR REPLACE FUNCTION update_departments_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER departments_updated_at_trigger
BEFORE UPDATE ON departments
FOR EACH ROW
EXECUTE FUNCTION update_departments_timestamp();

-- CATEGORIES TABLE
-- These CAN be created/managed by admins under each department

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

-- Create indexes
CREATE INDEX idx_categories_name ON categories(category_name);
CREATE INDEX idx_categories_department_id ON categories(department_id);
CREATE INDEX idx_categories_active ON categories(is_active);

-- Create trigger
CREATE OR REPLACE FUNCTION update_categories_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER categories_updated_at_trigger
BEFORE UPDATE ON categories
FOR EACH ROW
EXECUTE FUNCTION update_categories_timestamp();
