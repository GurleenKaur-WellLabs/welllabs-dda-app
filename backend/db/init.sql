CREATE EXTENSION IF NOT EXISTS postgis;

-- Users: email/password accounts, shared across all modules
CREATE TABLE users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email          TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    password_hash  TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Sessions: opaque token issued on login/register, read from an HttpOnly cookie
CREATE TABLE sessions (
    token       TEXT PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX sessions_user_id_idx ON sessions (user_id);

-- Organizations: a user can create/belong to many
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    created_by  UUID NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Org membership: any member can add users, only admins can remove them
CREATE TABLE org_members (
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    added_by    UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, user_id)
);

CREATE INDEX org_members_user_id_idx ON org_members (user_id);

-- Per-user QField Cloud tokens: each user links their own QField Cloud account
CREATE TABLE qfield_tokens (
    user_id           UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    qfield_username   TEXT NOT NULL,
    token             TEXT NOT NULL,
    expires_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Diagnosis: named work areas tied to a watershed boundary (owned by the Diagnose module)
CREATE TABLE diagnosis (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  TEXT NOT NULL,
    owner_id              UUID NOT NULL REFERENCES users(id),
    watershed_id          TEXT NOT NULL DEFAULT '',
    watershed_name        TEXT NOT NULL DEFAULT '',
    watershed_geom        GEOMETRY(Geometry, 4326),
    seed_lng              DOUBLE PRECISION NOT NULL,
    seed_lat              DOUBLE PRECISION NOT NULL,
    qfield_project_id     TEXT,
    qfield_project_owner  UUID REFERENCES users(id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX diagnosis_watershed_geom_idx ON diagnosis USING GIST (watershed_geom);
CREATE INDEX diagnosis_owner_id_idx ON diagnosis (owner_id);

-- Diagnosis sharing: direct user grants and org grants (owner manages both)
CREATE TABLE diagnosis_users (
    diagnosis_id  UUID NOT NULL REFERENCES diagnosis(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role          TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    added_by      UUID REFERENCES users(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (diagnosis_id, user_id)
);

CREATE TABLE diagnosis_orgs (
    diagnosis_id  UUID NOT NULL REFERENCES diagnosis(id) ON DELETE CASCADE,
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    added_by      UUID REFERENCES users(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (diagnosis_id, org_id)
);

CREATE INDEX diagnosis_users_user_id_idx ON diagnosis_users (user_id);
CREATE INDEX diagnosis_orgs_org_id_idx ON diagnosis_orgs (org_id);

-- Observation zones: polygon with text label + description (scoped to a diagnosis project)
CREATE TABLE observation_zones (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES diagnosis(id) ON DELETE CASCADE,
    geom        GEOMETRY(Geometry, 4326) NOT NULL,
    text        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '#0d983b',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  TEXT,
    CONSTRAINT observation_zones_geom_is_polygon CHECK (
        GeometryType(geom) IN ('POLYGON', 'MULTIPOLYGON')
    )
);

CREATE INDEX observation_zones_geom_idx ON observation_zones USING GIST (geom);
CREATE INDEX observation_zones_project_id_idx ON observation_zones (project_id);

-- Field notes: geotagged point with text and optional photo (scoped to a diagnosis project)
CREATE TABLE field_notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES diagnosis(id) ON DELETE CASCADE,
    geom        GEOMETRY(Point, 4326) NOT NULL,
    text        TEXT NOT NULL DEFAULT '',
    photo_path  TEXT,
    audio_path  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  TEXT
);

CREATE INDEX field_notes_geom_idx ON field_notes USING GIST (geom);
CREATE INDEX field_notes_project_id_idx ON field_notes (project_id);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER qfield_tokens_updated_at
    BEFORE UPDATE ON qfield_tokens
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER diagnosis_updated_at
    BEFORE UPDATE ON diagnosis
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER observation_zones_updated_at
    BEFORE UPDATE ON observation_zones
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER field_notes_updated_at
    BEFORE UPDATE ON field_notes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
