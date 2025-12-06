CREATE SCHEMA IF NOT EXISTS ontology;

CREATE TABLE IF NOT EXISTS ontology.hpo_edges (
  child_id  text NOT NULL,
  parent_id text NOT NULL,
  rel_type  text NOT NULL,              -- 'is_a', 'part_of', etc.
  source    text NOT NULL DEFAULT 'hpo',
  props     jsonb,
  PRIMARY KEY (child_id, parent_id, rel_type)
);

CREATE INDEX IF NOT EXISTS hpo_edges_child_idx  ON ontology.hpo_edges(child_id);
CREATE INDEX IF NOT EXISTS hpo_edges_parent_idx ON ontology.hpo_edges(parent_id);
