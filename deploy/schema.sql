-- Superviseur IA Comptable — schéma PostgreSQL (hébergement OVH, France)
-- Reprise à l'identique des tables de la base Supabase (relevé du 11/10/2026).
-- Exécuté automatiquement au premier démarrage du conteneur PostgreSQL.

CREATE TABLE IF NOT EXISTS smd_cabinets (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nom                    text NOT NULL,
    siret                  text DEFAULT '',
    pays                   text DEFAULT 'FR',
    plan                   text DEFAULT 'free',
    email_admin            text DEFAULT '',
    is_active              boolean DEFAULT true,
    created_at             timestamptz DEFAULT now(),
    stripe_customer_id     text DEFAULT '',
    stripe_subscription_id text DEFAULT '',
    quota_used_month       integer DEFAULT 0,
    quota_month            text DEFAULT '',
    updated_at             timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email                  varchar NOT NULL UNIQUE,
    role                   varchar NOT NULL DEFAULT 'client'
                           CHECK (role IN ('admin', 'cabinet', 'collaborateur', 'client', 'demo')),
    modules_allowed        text[] NOT NULL DEFAULT '{}',
    tenant_id              uuid REFERENCES smd_cabinets(id) ON DELETE SET NULL,
    full_name              varchar,
    company                varchar,
    is_active              boolean NOT NULL DEFAULT true,
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),
    password_hash          text DEFAULT '',
    nom                    text DEFAULT '',
    cabinet                text DEFAULT '',
    pays                   text DEFAULT 'FR',
    plan                   text DEFAULT 'free',
    quota_used_month       integer DEFAULT 0,
    quota_month            text DEFAULT '',
    stripe_customer_id     text DEFAULT '',
    stripe_subscription_id text DEFAULT '',
    last_login             timestamptz,
    last_seen              timestamptz
);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX IF NOT EXISTS users_tenant_id_idx ON users (tenant_id);

CREATE TABLE IF NOT EXISTS clients (
    id          bigserial PRIMARY KEY,
    nom         text NOT NULL,
    siret       text DEFAULT '',
    secteur     text DEFAULT '',
    contact     text DEFAULT '',
    email       text DEFAULT '',
    user_email  text DEFAULT '',
    created_at  timestamptz DEFAULT now(),
    tenant_id   uuid REFERENCES smd_cabinets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS clients_tenant_id_idx ON clients (tenant_id);

CREATE TABLE IF NOT EXISTS analyses (
    id            bigserial PRIMARY KEY,
    client_id     bigint REFERENCES clients(id) ON DELETE SET NULL,
    type_analyse  text,
    titre         text,
    contenu       text,
    exercice      text DEFAULT '',
    user_email    text DEFAULT '',
    expires_at    timestamptz,
    created_at    timestamptz DEFAULT now(),
    tenant_id     uuid REFERENCES smd_cabinets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS analyses_tenant_id_idx ON analyses (tenant_id);

CREATE TABLE IF NOT EXISTS smd_invitations (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    uuid NOT NULL REFERENCES smd_cabinets(id) ON DELETE CASCADE,
    email        text NOT NULL,
    role         text NOT NULL DEFAULT 'collaborateur' CHECK (role = 'collaborateur'),
    invited_by   text DEFAULT '',
    created_at   timestamptz DEFAULT now(),
    expires_at   timestamptz DEFAULT (now() + interval '30 days'),
    accepted_at  timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS smd_invitations_email_attente_idx
    ON smd_invitations (lower(email)) WHERE accepted_at IS NULL;
CREATE INDEX IF NOT EXISTS smd_invitations_tenant_id_idx ON smd_invitations (tenant_id);

CREATE TABLE IF NOT EXISTS smd_quota_usage (
    id           bigserial PRIMARY KEY,
    user_email   text,
    action_type  text,
    details      text DEFAULT '',
    month_year   text,
    created_at   timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id          bigserial PRIMARY KEY,
    user_id     uuid REFERENCES users(id),
    action      varchar NOT NULL,
    module      varchar,
    details     jsonb,
    ip_address  inet,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_logs_user ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_logs_date ON audit_logs (created_at DESC);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid REFERENCES users(id) ON DELETE CASCADE,
    module      varchar NOT NULL,
    messages    jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions (user_id);

CREATE TABLE IF NOT EXISTS demo_requests (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        varchar NOT NULL,
    email       varchar NOT NULL,
    company     varchar,
    status      varchar NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    expires_at  timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);
