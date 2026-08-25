CREATE TABLE IF NOT EXISTS schema_version (
  version integer PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content_category (
  id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL
);

CREATE TABLE IF NOT EXISTS system_string (
  id bigserial PRIMARY KEY,
  code text NOT NULL,
  locale text NOT NULL DEFAULT 'zh-CN',
  value text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  UNIQUE (code, locale)
);

CREATE TABLE IF NOT EXISTS project (
  id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE CHECK (code ~ '^P[0-9]{3,}$'),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  active_revision_id bigint,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_alias (
  id bigserial PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  alias_type text NOT NULL,
  alias text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS project_revision (
  id bigserial PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  code text NOT NULL UNIQUE,
  number integer NOT NULL,
  status text NOT NULL CHECK (status IN ('draft','published','abandoned')),
  based_on_id bigint REFERENCES project_revision(id),
  message text NOT NULL DEFAULT '',
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz,
  UNIQUE (project_id, number)
);

ALTER TABLE project DROP CONSTRAINT IF EXISTS project_active_revision_fk;
ALTER TABLE project ADD CONSTRAINT project_active_revision_fk
  FOREIGN KEY (active_revision_id) REFERENCES project_revision(id);

CREATE TABLE IF NOT EXISTS scenario (
  id bigserial PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  code text NOT NULL UNIQUE,
  slug text NOT NULL,
  name text NOT NULL,
  active_revision_id bigint,
  UNIQUE (project_id, slug)
);

CREATE TABLE IF NOT EXISTS scenario_revision (
  id bigserial PRIMARY KEY,
  scenario_id bigint NOT NULL REFERENCES scenario(id) ON DELETE CASCADE,
  project_revision_id bigint NOT NULL REFERENCES project_revision(id),
  code text NOT NULL UNIQUE,
  number integer NOT NULL,
  status text NOT NULL CHECK (status IN ('draft','published','abandoned')),
  created_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz,
  UNIQUE (scenario_id, number)
);

ALTER TABLE scenario DROP CONSTRAINT IF EXISTS scenario_active_revision_fk;
ALTER TABLE scenario ADD CONSTRAINT scenario_active_revision_fk
  FOREIGN KEY (active_revision_id) REFERENCES scenario_revision(id);

CREATE TABLE IF NOT EXISTS module (
  id bigserial PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  code text NOT NULL UNIQUE,
  kind text NOT NULL,
  name text NOT NULL,
  sort_order integer NOT NULL
);

CREATE TABLE IF NOT EXISTS module_version (
  id bigserial PRIMARY KEY,
  module_id bigint NOT NULL REFERENCES module(id) ON DELETE CASCADE,
  project_revision_id bigint NOT NULL REFERENCES project_revision(id),
  sort_order integer NOT NULL,
  visible boolean NOT NULL DEFAULT true,
  UNIQUE (module_id, project_revision_id)
);

CREATE TABLE IF NOT EXISTS source_document (
  id bigserial PRIMARY KEY,
  project_id bigint REFERENCES project(id) ON DELETE CASCADE,
  code text NOT NULL UNIQUE,
  kind text NOT NULL,
  title text NOT NULL
);

CREATE TABLE IF NOT EXISTS source_version (
  id bigserial PRIMARY KEY,
  source_id bigint NOT NULL REFERENCES source_document(id) ON DELETE CASCADE,
  version integer NOT NULL,
  sha256 text NOT NULL CHECK (length(sha256) = 64),
  object_path text NOT NULL,
  media_type text NOT NULL,
  bytes bigint NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, version)
);

CREATE TABLE IF NOT EXISTS content_field (
  id bigserial PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  module_id bigint NOT NULL REFERENCES module(id) ON DELETE CASCADE,
  category_id bigint REFERENCES content_category(id),
  code text NOT NULL UNIQUE,
  role text NOT NULL,
  data_type text NOT NULL DEFAULT 'text',
  sort_order integer NOT NULL,
  source_type text NOT NULL CHECK (source_type IN ('import','manual','computed','system')),
  source_version_id bigint REFERENCES source_version(id),
  formula text,
  visible_scenarios text[] NOT NULL DEFAULT '{}'::text[],
  sensitivity text NOT NULL DEFAULT 'public',
  created_revision_id bigint NOT NULL REFERENCES project_revision(id),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS content_value (
  id bigserial PRIMARY KEY,
  field_id bigint NOT NULL REFERENCES content_field(id) ON DELETE CASCADE,
  project_revision_id bigint NOT NULL REFERENCES project_revision(id) ON DELETE CASCADE,
  value jsonb NOT NULL,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (field_id, project_revision_id)
);

CREATE TABLE IF NOT EXISTS scenario_override (
  id bigserial PRIMARY KEY,
  scenario_revision_id bigint NOT NULL REFERENCES scenario_revision(id) ON DELETE CASCADE,
  field_id bigint NOT NULL REFERENCES content_field(id) ON DELETE CASCADE,
  value jsonb,
  visible boolean,
  sort_order integer,
  version integer NOT NULL DEFAULT 1,
  UNIQUE (scenario_revision_id, field_id)
);

CREATE TABLE IF NOT EXISTS asset (
  id bigserial PRIMARY KEY,
  project_id bigint REFERENCES project(id) ON DELETE CASCADE,
  module_id bigint REFERENCES module(id) ON DELETE SET NULL,
  code text NOT NULL UNIQUE,
  role text NOT NULL,
  title text NOT NULL,
  sort_order integer NOT NULL DEFAULT 0,
  visible_scenarios text[] NOT NULL DEFAULT '{}'::text[],
  created_revision_id bigint NOT NULL REFERENCES project_revision(id)
);

CREATE TABLE IF NOT EXISTS asset_version (
  id bigserial PRIMARY KEY,
  asset_id bigint NOT NULL REFERENCES asset(id) ON DELETE CASCADE,
  version integer NOT NULL,
  sha256 text NOT NULL CHECK (length(sha256) = 64),
  object_path text NOT NULL,
  media_type text NOT NULL,
  bytes bigint NOT NULL,
  width integer,
  height integer,
  source_version_id bigint REFERENCES source_version(id),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (asset_id, version)
);

ALTER TABLE source_version DROP CONSTRAINT IF EXISTS source_version_sha256_object_path_key;
ALTER TABLE asset_version DROP CONSTRAINT IF EXISTS asset_version_sha256_object_path_key;

CREATE TABLE IF NOT EXISTS asset_binding (
  id bigserial PRIMARY KEY,
  asset_id bigint NOT NULL REFERENCES asset(id) ON DELETE CASCADE,
  project_revision_id bigint NOT NULL REFERENCES project_revision(id) ON DELETE CASCADE,
  asset_version_id bigint NOT NULL REFERENCES asset_version(id),
  visible boolean NOT NULL DEFAULT true,
  UNIQUE (asset_id, project_revision_id)
);

CREATE TABLE IF NOT EXISTS artifact_definition (
  id bigserial PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  scenario_id bigint NOT NULL REFERENCES scenario(id) ON DELETE CASCADE,
  code text NOT NULL UNIQUE,
  kind text NOT NULL,
  slug text NOT NULL,
  active_build_id bigint,
  UNIQUE (scenario_id, kind, slug)
);

CREATE TABLE IF NOT EXISTS artifact_build (
  id bigserial PRIMARY KEY,
  artifact_definition_id bigint NOT NULL REFERENCES artifact_definition(id) ON DELETE CASCADE,
  project_revision_id bigint NOT NULL REFERENCES project_revision(id),
  scenario_revision_id bigint NOT NULL REFERENCES scenario_revision(id),
  number integer NOT NULL,
  status text NOT NULL CHECK (status IN ('building','ready','failed')),
  checksum text NOT NULL,
  output_path text NOT NULL,
  output_text text,
  coverage jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (artifact_definition_id, number)
);

ALTER TABLE artifact_definition DROP CONSTRAINT IF EXISTS artifact_definition_active_build_fk;
ALTER TABLE artifact_definition ADD CONSTRAINT artifact_definition_active_build_fk
  FOREIGN KEY (active_build_id) REFERENCES artifact_build(id);

CREATE TABLE IF NOT EXISTS artifact_field_map (
  id bigserial PRIMARY KEY,
  build_id bigint NOT NULL REFERENCES artifact_build(id) ON DELETE CASCADE,
  field_id bigint REFERENCES content_field(id),
  asset_id bigint REFERENCES asset(id),
  location text NOT NULL,
  CHECK ((field_id IS NOT NULL) <> (asset_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS change_event (
  id bigserial PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  revision_id bigint REFERENCES project_revision(id),
  kind text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS migration_hold (
  id bigserial PRIMARY KEY,
  path text NOT NULL UNIQUE,
  sha256 text NOT NULL,
  reason text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION notify_project_change() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('project_change', json_build_object(
    'event_id', NEW.id,
    'project_id', NEW.project_id,
    'revision_id', NEW.revision_id,
    'kind', NEW.kind
  )::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS project_change_notify ON change_event;
CREATE TRIGGER project_change_notify AFTER INSERT ON change_event
FOR EACH ROW EXECUTE FUNCTION notify_project_change();

CREATE OR REPLACE FUNCTION reject_published_content_change() RETURNS trigger AS $$
DECLARE revision_status text;
BEGIN
  SELECT status INTO revision_status FROM project_revision WHERE id = COALESCE(NEW.project_revision_id, OLD.project_revision_id);
  IF revision_status = 'published' THEN
    RAISE EXCEPTION 'published revisions are immutable';
  END IF;
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS immutable_published_content ON content_value;
CREATE TRIGGER immutable_published_content BEFORE UPDATE OR DELETE ON content_value
FOR EACH ROW EXECUTE FUNCTION reject_published_content_change();

INSERT INTO schema_version(version) VALUES (1) ON CONFLICT DO NOTHING;
