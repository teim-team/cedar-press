-- Disposable test fixtures live separately from persistent development data.
CREATE DATABASE cedar_press_test;
\connect cedar_press_test
-- Existing contract tests also exercise the optional teim-app account link.
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    workspace_tier TEXT
);
