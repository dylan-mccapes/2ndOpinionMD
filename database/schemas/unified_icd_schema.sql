
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'pgvector extension not available, continuing without vector support';
END
$$;

DROP TABLE IF EXISTS ontology.code_cross_references CASCADE;
DROP TABLE IF EXISTS ontology.icd CASCADE;

DO $$
BEGIN
    EXECUTE '
    CREATE TABLE ontology.icd (
        code TEXT PRIMARY KEY,
        title TEXT,
        definition TEXT,
        system TEXT, -- ''ICD-10-CM'' or ''ICD-11''
        version TEXT,
        parent_code TEXT,
        chapter TEXT,
        section TEXT,
        full_path TEXT[],
        depth SMALLINT,
        search_content TEXT,
        foundation_uri TEXT, -- ICD-11 specific
        linearization_uri TEXT, -- ICD-11 specific
        class_kind TEXT, -- ICD-11: ''chapter'', ''block'', ''category''
        is_residual BOOLEAN DEFAULT FALSE, -- ICD-11 specific
        metadata JSONB, -- Additional metadata
        term_vector vector(1536), -- OpenAI embeddings
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (parent_code) REFERENCES ontology.icd(code)
    )';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Creating table without vector support';
    EXECUTE '
    CREATE TABLE ontology.icd (
        code TEXT PRIMARY KEY,
        title TEXT,
        definition TEXT,
        system TEXT, -- ''ICD-10-CM'' or ''ICD-11''
        version TEXT,
        parent_code TEXT,
        chapter TEXT,
        section TEXT,
        full_path TEXT[],
        depth SMALLINT,
        search_content TEXT,
        foundation_uri TEXT, -- ICD-11 specific
        linearization_uri TEXT, -- ICD-11 specific
        class_kind TEXT, -- ICD-11: ''chapter'', ''block'', ''category''
        is_residual BOOLEAN DEFAULT FALSE, -- ICD-11 specific
        metadata JSONB, -- Additional metadata
        term_vector_json TEXT, -- OpenAI embeddings as JSON fallback
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (parent_code) REFERENCES ontology.icd(code)
    )';
END
$$;

CREATE TABLE ontology.code_cross_references (
    id SERIAL PRIMARY KEY,
    source_table TEXT DEFAULT 'ontology.icd',
    source_id TEXT,
    target_table TEXT DEFAULT 'ontology.icd',
    target_id TEXT,
    relationship_type TEXT, -- 'equivalent', 'broader', 'narrower'
    confidence DECIMAL(3,2),
    similarity_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (source_id) REFERENCES ontology.icd(code),
    FOREIGN KEY (target_id) REFERENCES ontology.icd(code)
);

CREATE INDEX idx_icd_system ON ontology.icd(system);
CREATE INDEX idx_icd_parent_code ON ontology.icd(parent_code);
CREATE INDEX idx_icd_version ON ontology.icd(version);
CREATE INDEX idx_icd_full_path ON ontology.icd USING GIN(full_path);
CREATE INDEX idx_icd_class_kind ON ontology.icd(class_kind);
CREATE INDEX idx_icd_foundation_uri ON ontology.icd(foundation_uri);
DO $$
BEGIN
    EXECUTE 'CREATE INDEX idx_icd_vector ON ontology.icd USING ivfflat (term_vector vector_cosine_ops) WITH (lists = 100)';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Vector index not created - pgvector not available';
END
$$;

CREATE INDEX idx_cross_ref_source ON ontology.code_cross_references(source_id);
CREATE INDEX idx_cross_ref_target ON ontology.code_cross_references(target_id);
CREATE INDEX idx_cross_ref_confidence ON ontology.code_cross_references(confidence);
CREATE INDEX idx_cross_ref_relationship ON ontology.code_cross_references(relationship_type);

GRANT ALL PRIVILEGES ON SCHEMA ontology TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ontology TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ontology TO postgres;
