#!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

def get_database_url():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        user = os.environ.get("DB_USER", "devin")
        password = os.environ.get("DB_PASSWORD", "devin123")
        database = os.environ.get("DB_NAME", "2ndopinionmd")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    elif db_url.startswith("postgresql+asyncpg://"):
        db_url = "postgresql://" + db_url.split("postgresql+asyncpg://", 1)[1]
    
    return db_url

def setup_schema():
    try:
        conn = psycopg2.connect(get_database_url())
        cur = conn.cursor()
        
        print("🔧 Setting up ClinGen Actionability schema...")
        
        cur.execute("CREATE SCHEMA IF NOT EXISTS clingen")
        print("  ✅ Schema 'clingen' created")
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clingen.actionability_summary (
            cohort TEXT,
            gene_symbol TEXT,
            hgnc_id TEXT,
            disease_name TEXT,
            disease_mondo_id TEXT,
            actionability_assertion TEXT,
            report_date DATE,
            source_url TEXT
        )
        """)
        print("  ✅ Table 'actionability_summary' created")
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clingen.actionability_scoring (
            cohort TEXT,
            gene_symbol TEXT,
            hgnc_id TEXT,
            disease_name TEXT,
            disease_mondo_id TEXT,
            score NUMERIC,
            evidence_type TEXT
        )
        """)
        print("  ✅ Table 'actionability_scoring' created")
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clingen.actionability_assertions (
            cohort TEXT,
            gene_symbol TEXT,
            hgnc_id TEXT,
            disease_name TEXT,
            disease_mondo_id TEXT,
            assertion_type TEXT,
            assertion_description TEXT
        )
        """)
        print("  ✅ Table 'actionability_assertions' created")
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clingen.variant_pathogenicity (
            gene_symbol TEXT,
            hgnc_id TEXT,
            variant_name TEXT,
            classification TEXT,
            last_evaluated DATE,
            review_status TEXT,
            condition_name TEXT,
            condition_identifiers TEXT
        )
        """)
        print("  ✅ Table 'variant_pathogenicity' created")
        
        print("🧪 Inserting sample test data...")
        
        cur.execute("DELETE FROM clingen.actionability_summary")
        cur.execute("DELETE FROM clingen.actionability_scoring")
        cur.execute("DELETE FROM clingen.actionability_assertions")
        cur.execute("DELETE FROM clingen.variant_pathogenicity")
        
        cur.execute("""
        INSERT INTO clingen.actionability_summary (cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, actionability_assertion, report_date, source_url) VALUES 
        ('Adult', 'BRCA1', 'HGNC:1100', 'Breast cancer', 'MONDO:0007254', 'Definitive', '2024-01-01', 'https://actionability.clinicalgenome.org'),
        ('Pediatric', 'BRCA2', 'HGNC:1101', 'Ovarian cancer', 'MONDO:0008170', 'Strong', '2024-01-02', 'https://actionability.clinicalgenome.org'),
        ('Adult', 'TP53', 'HGNC:11998', 'Li-Fraumeni syndrome', 'MONDO:0007893', 'Definitive', '2024-01-03', 'https://actionability.clinicalgenome.org'),
        ('Adult', 'MLH1', 'HGNC:7127', 'Lynch syndrome', 'MONDO:0018084', 'Strong', '2024-01-04', 'https://actionability.clinicalgenome.org'),
        ('Adult', 'BRCA1', 'HGNC:1100', 'Breast cancer', 'MONDO:0007254', 'Definitive', '2024-01-05', 'https://actionability.clinicalgenome.org'),
        ('Pediatric', 'BRCA1', 'HGNC:1100', 'Breast cancer', 'MONDO:0007254', 'Strong', '2024-01-06', 'https://actionability.clinicalgenome.org')
        """)
        
        cur.execute("""
        INSERT INTO clingen.actionability_scoring (cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, score, evidence_type) VALUES
        ('Adult', 'BRCA1', 'HGNC:1100', 'Breast cancer', 'MONDO:0007254', 8.5, 'Research'),
        ('Pediatric', 'BRCA2', 'HGNC:1101', 'Ovarian cancer', 'MONDO:0008170', 7.2, 'Clinical'),
        ('Adult', 'TP53', 'HGNC:11998', 'Li-Fraumeni syndrome', 'MONDO:0007893', 9.1, 'Research'),
        ('Adult', 'MLH1', 'HGNC:7127', 'Lynch syndrome', 'MONDO:0018084', 6.8, 'Clinical'),
        ('Adult', 'BRCA1', 'HGNC:1100', 'Breast cancer', 'MONDO:0007254', 9.2, 'Clinical'),
        ('Pediatric', 'BRCA1', 'HGNC:1100', 'Breast cancer', 'MONDO:0007254', 7.8, 'Research')
        """)
        
        cur.execute("""
        INSERT INTO clingen.actionability_assertions (cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, assertion_type, assertion_description) VALUES
        ('Adult', 'BRCA1', 'HGNC:1100', 'Breast cancer', 'MONDO:0007254', 'Actionable', 'Strong evidence for actionability'),
        ('Pediatric', 'BRCA2', 'HGNC:1101', 'Ovarian cancer', 'MONDO:0008170', 'Actionable', 'Moderate evidence for actionability')
        """)
        
        cur.execute("""
        INSERT INTO clingen.variant_pathogenicity (gene_symbol, hgnc_id, variant_name, classification, last_evaluated, review_status, condition_name, condition_identifiers) VALUES
        ('BRCA1', 'HGNC:1100', 'c.68_69delAG', 'Pathogenic', '2024-01-01', 'Reviewed', 'Breast cancer', 'MONDO:0007254'),
        ('BRCA2', 'HGNC:1101', 'c.5946delT', 'Pathogenic', '2024-01-02', 'Reviewed', 'Ovarian cancer', 'MONDO:0008170')
        """)
        
        print("  ✅ Sample test data inserted")
        
        print("🔧 Creating improved materialized view with DISTINCT ON...")
        
        cur.execute("DROP MATERIALIZED VIEW IF EXISTS clingen.v_actionability_quick")
        cur.execute("""
        CREATE MATERIALIZED VIEW clingen.v_actionability_quick AS
        SELECT DISTINCT ON (s.cohort, s.hgnc_id,
                            COALESCE(s.disease_mondo_id, s.disease_name),
                            COALESCE(sc.evidence_type,'~'),
                            COALESCE(s.report_date, DATE '0001-01-01'))
          s.cohort,
          s.gene_symbol,
          s.hgnc_id,
          s.disease_name,
          s.disease_mondo_id,
          COALESCE(s.disease_mondo_id, s.disease_name) AS disease_key,
          s.actionability_assertion,
          sc.score,
          sc.evidence_type,
          s.report_date
        FROM clingen.actionability_summary s
        LEFT JOIN clingen.actionability_scoring sc
          ON sc.cohort = s.cohort
         AND sc.hgnc_id = s.hgnc_id
         AND COALESCE(sc.disease_mondo_id, sc.disease_name)
             = COALESCE(s.disease_mondo_id, s.disease_name)
        ORDER BY
          s.cohort, s.hgnc_id,
          COALESCE(s.disease_mondo_id, s.disease_name),
          COALESCE(sc.evidence_type,'~'),
          COALESCE(s.report_date, DATE '0001-01-01') DESC,
          COALESCE(sc.score, -1) DESC
        """)
        print("  ✅ Materialized view 'v_actionability_quick' created with DISTINCT ON")
        
        cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_v_act_quick_unique
        ON clingen.v_actionability_quick
          (cohort, hgnc_id, disease_key,
           COALESCE(evidence_type,'~'),
           COALESCE(report_date, DATE '0001-01-01'))
        """)
        print("  ✅ Unique index 'idx_v_act_quick_unique' created for concurrent refresh")
        
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_v_actionability_quick_cohort_gene 
        ON clingen.v_actionability_quick (cohort, gene_symbol)
        """)
        print("  ✅ Performance index 'idx_v_actionability_quick_cohort_gene' created")
        
        conn.commit()
        conn.close()
        print("✅ ClinGen Actionability schema and improved materialized view setup complete!")
        
    except Exception as e:
        print(f"❌ Error setting up ClinGen Actionability schema: {e}")
        raise

if __name__ == "__main__":
    setup_schema()
