-- The application connects with a role that is NOT a superuser and has NOBYPASSRLS:
-- PostgreSQL never applies Row-Level Security to superusers (CLAUDE.md §5).
-- The role owns the database (migrations) and can create the pytest database.
CREATE ROLE wedivo LOGIN PASSWORD 'wedivo' NOSUPERUSER NOBYPASSRLS CREATEDB;
CREATE DATABASE wedivo OWNER wedivo;
