-- Create test database if it doesn't exist
SELECT 'CREATE DATABASE aicte_dashboard_test OWNER aicte'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'aicte_dashboard_test')\gexec
