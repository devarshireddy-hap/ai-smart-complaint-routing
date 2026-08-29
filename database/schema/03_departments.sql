-- Departments Table
-- Stores complaint handling departments (TECHNICAL, FINANCE, ELECTRICAL, PLUMBING, SECURITY)

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

-- Create indexes
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

-- Categories Table
-- Stores complaint categories/types

CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    department_id INTEGER REFERENCES departments(department_id) ON DELETE CASCADE,
    sla_hours INTEGER DEFAULT 24, -- Service Level Agreement in hours
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_categories_name ON categories(category_name);
CREATE INDEX idx_categories_department_id ON categories(department_id);
CREATE INDEX idx_categories_active ON categories(is_active);

-- Create trigger to update updated_at
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
