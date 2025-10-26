DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(100) NOT NULL UNIQUE,
    department_id INTEGER REFERENCES departments(id) ON DELETE CASCADE,
    is_busy BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    id_author VARCHAR(100),
    department_id INTEGER REFERENCES departments(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    assigned_employee_id VARCHAR(100) REFERENCES employees(employee_id) ON DELETE SET NULL
);

CREATE OR REPLACE FUNCTION assign_pending_documents_to_employee(
    free_employee_id VARCHAR(100)
)
RETURNS VOID AS $$
DECLARE
    pending_doc RECORD;
    employee_dept_id INTEGER;
BEGIN
    SELECT department_id INTO employee_dept_id 
    FROM employees 
    WHERE employee_id = free_employee_id;
    
    SELECT * INTO pending_doc
    FROM documents 
    WHERE 
        assigned_employee_id IS NULL AND
        department_id = employee_dept_id
    ORDER BY id
    LIMIT 1;
    
    IF FOUND THEN
        UPDATE documents 
        SET assigned_employee_id = free_employee_id
        WHERE id = pending_doc.id;
        
        UPDATE employees 
        SET is_busy = TRUE 
        WHERE employee_id = free_employee_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION assign_all_free_employees()
RETURNS VOID AS $$
DECLARE
    free_employee RECORD;
BEGIN
    FOR free_employee IN 
        SELECT employee_id 
        FROM employees 
        WHERE is_busy = FALSE
    LOOP

        PERFORM assign_pending_documents_to_employee(free_employee.employee_id);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION auto_assign_employee()
RETURNS TRIGGER AS $$
BEGIN
    SELECT e.employee_id INTO NEW.assigned_employee_id
    FROM employees e
    WHERE
        e.department_id = NEW.department_id AND
        e.is_busy = FALSE
    ORDER BY random()
    LIMIT 1;

    IF FOUND THEN
        UPDATE employees
        SET is_busy = TRUE
        WHERE employee_id = NEW.assigned_employee_id;
    ELSE
        NEW.assigned_employee_id := NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION release_employee_on_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.assigned_employee_id IS NOT NULL THEN
        UPDATE employees
        SET is_busy = FALSE
        WHERE employee_id = OLD.assigned_employee_id;
        
        PERFORM assign_pending_documents_to_employee(OLD.assigned_employee_id);
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION on_employee_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_busy = FALSE AND OLD.is_busy = TRUE THEN
        PERFORM assign_pending_documents_to_employee(NEW.employee_id);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION balance_assignments()
RETURNS TABLE(
    assigned_documents INTEGER,
    pending_documents INTEGER,
    free_employees INTEGER
) AS $$
DECLARE
    assigned_count INTEGER := 0;
BEGIN
    PERFORM assign_all_free_employees();
    
    RETURN QUERY
    SELECT 
        COUNT(CASE WHEN d.assigned_employee_id IS NOT NULL THEN 1 END)::INTEGER as assigned_documents,
        COUNT(CASE WHEN d.assigned_employee_id IS NULL THEN 1 END)::INTEGER as pending_documents,
        COUNT(CASE WHEN e.is_busy = FALSE THEN 1 END)::INTEGER as free_employees
    FROM documents d
    CROSS JOIN employees e;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_assign_employee
    BEFORE INSERT ON documents
    FOR EACH ROW
    EXECUTE FUNCTION auto_assign_employee();

CREATE TRIGGER trigger_release_employee_on_delete
    AFTER DELETE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION release_employee_on_delete();

CREATE TRIGGER trigger_employee_status_change
    AFTER UPDATE OF is_busy ON employees
    FOR EACH ROW
    EXECUTE FUNCTION on_employee_status_change();
