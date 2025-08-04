
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'pgvector extension not available, continuing without vector support';
END
$$;

DO $$
BEGIN
    EXECUTE '
    CREATE TABLE ontology.hpo_terms (
        hpo_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        definition TEXT,
        synonyms TEXT[],
        parent_ids TEXT[],
        depth SMALLINT DEFAULT 0,
        is_obsolete BOOLEAN DEFAULT FALSE,
        metadata JSONB,
        term_vec vector(1536),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Creating HPO terms table without vector support';
    EXECUTE '
    CREATE TABLE ontology.hpo_terms (
        hpo_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        definition TEXT,
        synonyms TEXT[],
        parent_ids TEXT[],
        depth SMALLINT DEFAULT 0,
        is_obsolete BOOLEAN DEFAULT FALSE,
        metadata JSONB,
        term_vec_json TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )';
END
$$;

CREATE TABLE ontology.hpo_disease_links (
    id SERIAL PRIMARY KEY,
    database_id TEXT NOT NULL,
    disease_name TEXT NOT NULL,
    qualifier TEXT,
    hpo_id TEXT NOT NULL,
    reference TEXT,
    evidence TEXT,
    onset TEXT,
    frequency TEXT,
    sex TEXT,
    modifier TEXT,
    aspect TEXT,
    biocuration TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (hpo_id) REFERENCES ontology.hpo_terms(hpo_id)
);

CREATE INDEX idx_hpo_terms_name ON ontology.hpo_terms(name);
CREATE INDEX idx_hpo_terms_parent_ids ON ontology.hpo_terms USING GIN(parent_ids);
CREATE INDEX idx_hpo_terms_depth ON ontology.hpo_terms(depth);
CREATE INDEX idx_hpo_terms_obsolete ON ontology.hpo_terms(is_obsolete);

DO $$
BEGIN
    EXECUTE 'CREATE INDEX idx_hpo_terms_vector ON ontology.hpo_terms USING ivfflat (term_vec vector_cosine_ops) WITH (lists = 100)';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Vector index not created - pgvector not available';
END
$$;

CREATE INDEX idx_hpo_disease_links_database_id ON ontology.hpo_disease_links(database_id);
CREATE INDEX idx_hpo_disease_links_hpo_id ON ontology.hpo_disease_links(hpo_id);
CREATE INDEX idx_hpo_disease_links_disease_name ON ontology.hpo_disease_links(disease_name);
CREATE INDEX idx_hpo_disease_links_evidence ON ontology.hpo_disease_links(evidence);

GRANT ALL PRIVILEGES ON TABLE ontology.hpo_terms TO postgres;
GRANT ALL PRIVILEGES ON TABLE ontology.hpo_disease_links TO postgres;
GRANT ALL PRIVILEGES ON SEQUENCE ontology.hpo_disease_links_id_seq TO postgres;
