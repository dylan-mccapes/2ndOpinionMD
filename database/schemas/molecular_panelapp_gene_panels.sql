-- 012_panelapp_gene_panels.sql
-- Schema + trigger-maintained tsvector + indexes for fast lookup

CREATE SCHEMA IF NOT EXISTS molecular;

CREATE TABLE IF NOT EXISTS molecular.gene_panels (
  panel_id                INTEGER      NOT NULL,
  panel_hash_id           TEXT         NULL,
  panel_name              TEXT         NOT NULL,
  panel_version           TEXT         NOT NULL,         -- e.g. '1.73'
  signed_off              BOOLEAN      NOT NULL DEFAULT false,
  source_instance         TEXT         NOT NULL DEFAULT 'GEL',  -- 'GEL' or 'AUS'
  disease_group           TEXT         NULL,
  disease_sub_group       TEXT         NULL,
  relevant_disorders      TEXT[]       NULL,
  panel_types             TEXT[]       NULL,

  gene_symbol             TEXT         NOT NULL,
  hgnc_id                 TEXT         NULL,
  ensembl_gene_id_grch37  TEXT         NULL,
  ensembl_gene_id_grch38  TEXT         NULL,
  confidence_level        TEXT         NULL,            -- 'High' (green), 'Moderate' (amber), 'Low' (red)
  mode_of_inheritance     TEXT         NULL,
  evidence                TEXT[]       NULL,
  phenotypes              TEXT[]       NULL,
  review_status           TEXT         NULL,

  raw_panel_json          JSONB        NULL,
  raw_gene_json           JSONB        NULL,

  ts                      TSVECTOR     NULL,            -- maintained by trigger
  imported_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),

  PRIMARY KEY (panel_id, panel_version, gene_symbol)
);

-- Trigger to maintain FTS vector
CREATE OR REPLACE FUNCTION molecular.gp_ts_update() RETURNS trigger AS $$
BEGIN
  NEW.ts :=
    setweight(to_tsvector('english', coalesce(NEW.panel_name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.gene_symbol, '')), 'A') ||
    setweight(to_tsvector('english', array_to_string(NEW.relevant_disorders, ' ')), 'B') ||
    setweight(to_tsvector('english', array_to_string(NEW.phenotypes, ' ')), 'C') ||
    setweight(to_tsvector('english', array_to_string(NEW.evidence, ' ')), 'D');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_gp_ts ON molecular.gene_panels;
CREATE TRIGGER trg_gp_ts
BEFORE INSERT OR UPDATE OF panel_name, gene_symbol, relevant_disorders, phenotypes, evidence
ON molecular.gene_panels
FOR EACH ROW EXECUTE FUNCTION molecular.gp_ts_update();

-- Backfill ts for existing rows (idempotent, no trailing commas)
UPDATE molecular.gene_panels
SET ts =
    setweight(to_tsvector('english', coalesce(panel_name, '')), 'A')
 || setweight(to_tsvector('english', coalesce(gene_symbol, '')), 'A')
 || setweight(to_tsvector('english', coalesce(array_to_string(relevant_disorders, ' '), '')), 'B')
 || setweight(to_tsvector('english', coalesce(array_to_string(phenotypes, ' '), '')), 'C')
 || setweight(to_tsvector('english', coalesce(array_to_string(evidence, ' '), '')), 'D')
WHERE ts IS NULL OR ts = '';

-- Helper MV for latest version per panel (by version segments; fallback to imported_at)
CREATE MATERIALIZED VIEW IF NOT EXISTS molecular.v_gene_panels_latest AS
WITH ranked AS (
  SELECT gp.*,
         ROW_NUMBER() OVER (
           PARTITION BY gp.panel_id
           ORDER BY
             split_part(gp.panel_version,'.',1)::int DESC,
             split_part(gp.panel_version,'.',2)::int DESC,
             split_part(gp.panel_version,'.',3)::int DESC,
             gp.imported_at DESC
         ) AS rn
  FROM molecular.gene_panels gp
)
SELECT * FROM ranked WHERE rn = 1;

CREATE INDEX IF NOT EXISTS v_gp_latest_panel ON molecular.v_gene_panels_latest (panel_id);
