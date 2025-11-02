-- database/sql/snomed_add_indexes.sql

-- consolidated
DO $$
BEGIN
  IF to_regclass('ontology.snomed') IS NOT NULL THEN
    -- conceptId lookup
    EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS snomed_conceptid_idx ON ontology.snomed (conceptid)';
    -- full-text across FSN + synonyms
    EXECUTE $x$
      CREATE INDEX IF NOT EXISTS snomed_fts_idx
      ON ontology.snomed
      USING gin (to_tsvector('english',
                 coalesce(fsn,'') || ' ' || coalesce(array_to_string(synonyms,' '),'')));
    $x$;
  END IF;
END$$;

-- RF2
DO $$
BEGIN
  IF to_regclass('ontology.snomed_concepts') IS NOT NULL THEN
    EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS snomed_concepts_pk_idx ON ontology.snomed_concepts (conceptid)';
  END IF;

  IF to_regclass('ontology.snomed_descriptions') IS NOT NULL THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS snomed_desc_concept_idx ON ontology.snomed_descriptions (conceptid)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS snomed_desc_type_active_idx ON ontology.snomed_descriptions (typeid, active)';
    EXECUTE $y$
      CREATE INDEX IF NOT EXISTS snomed_desc_fts_idx
      ON ontology.snomed_descriptions
      USING gin (to_tsvector('english', coalesce(term,'')));
    $y$;
  END IF;

  IF to_regclass('ontology.snomed_relationships') IS NOT NULL THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS snomed_rel_src_idx ON ontology.snomed_relationships (sourceid)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS snomed_rel_dst_idx ON ontology.snomed_relationships (destinationid)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS snomed_rel_type_active_idx ON ontology.snomed_relationships (typeid, active)';
  END IF;
END$$;

