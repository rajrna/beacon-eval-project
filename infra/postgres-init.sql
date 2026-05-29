-- Run once on first database init
-- Enables UUID generation and other extensions needed by Beacon

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For future full-text search on traces
