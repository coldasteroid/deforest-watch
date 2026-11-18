-- Create the DeforestWatch role, database and PostGIS extension.
--
-- Run once as a superuser against a PostgreSQL server that already has the
-- PostGIS extension files installed:
--
--   psql -U postgres -h localhost -p 5432 -f infra/bootstrap_db.sql
--
-- The credentials match infra/docker-compose.yml and .env.example, so the
-- native and container paths are interchangeable. They are development
-- credentials for a loopback database and are not secrets; change them for
-- anything reachable from outside the machine.
--
-- Safe to re-run: ON_ERROR_STOP is off deliberately, so "already exists"
-- notices do not abort the script.

\set ON_ERROR_STOP off

CREATE ROLE dw LOGIN PASSWORD 'dw';
ALTER ROLE dw LOGIN PASSWORD 'dw';

CREATE DATABASE deforestwatch OWNER dw;

\connect deforestwatch

CREATE EXTENSION IF NOT EXISTS postgis;
ALTER SCHEMA public OWNER TO dw;
GRANT ALL ON SCHEMA public TO dw;

SELECT postgis_full_version() AS postgis;
SELECT current_database() AS database, current_user AS connected_as;
