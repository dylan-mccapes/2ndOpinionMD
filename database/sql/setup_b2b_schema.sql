-- B2B API infrastructure: tenants, API keys, usage metering
-- Run once: psql "$SYNC_DATABASE_URL" -f database/sql/setup_b2b_schema.sql

BEGIN;

CREATE SCHEMA IF NOT EXISTS b2b;

-- Tenants (organizations that hold API keys)
CREATE TABLE IF NOT EXISTS b2b.tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    contact_email   TEXT NOT NULL,
    plan            TEXT NOT NULL DEFAULT 'free',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_name ON b2b.tenants (name);

-- API keys (hashed; raw key shown once at creation)
CREATE TABLE IF NOT EXISTS b2b.api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    key_hash        TEXT NOT NULL UNIQUE,
    key_prefix      TEXT NOT NULL,
    key_last4       TEXT NOT NULL,
    name            TEXT,
    scopes          TEXT[] NOT NULL DEFAULT '{}',
    rate_limit_rpm  INT NOT NULL DEFAULT 60,
    rate_limit_rpd  INT NOT NULL DEFAULT 10000,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON b2b.api_keys (tenant_id);

-- Usage events (append-only metering log)
CREATE TABLE IF NOT EXISTS b2b.usage_events (
    id              BIGSERIAL PRIMARY KEY,
    api_key_id      UUID NOT NULL REFERENCES b2b.api_keys(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL,
    endpoint        TEXT NOT NULL,
    method          TEXT NOT NULL,
    status_code     INT,
    response_ms     INT,
    tokens_used     INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_tenant_date
    ON b2b.usage_events (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_key_date
    ON b2b.usage_events (api_key_id, created_at);

-- Partition-friendly: monthly partitioning can be added later with
--   ALTER TABLE b2b.usage_events ... PARTITION BY RANGE (created_at);

COMMIT;
