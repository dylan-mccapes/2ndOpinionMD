#!/usr/bin/env python3
"""
SNOMED CT Data Ingestion Script

Loads SNOMED CT RF2 data from US Edition into PostgreSQL ontology schema.
Supports schema-aware loading with idempotent upserts.
"""

import argparse
import csv
import os
import sys
import tempfile
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2_147_483_647)  # fallback for platforms that cap at 2^31-1

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

def get_database_url() -> str:
    """Get database URL from environment with fallbacks"""
    fallbacks = [
        "postgresql://postgres:postgres@localhost/2ndopinionmd",
        "host=localhost dbname=2ndopinionmd user=postgres password=postgres",
        "postgresql://postgres@localhost/2ndopinionmd",
        "host=localhost dbname=2ndopinionmd user=postgres",
        "postgresql:///2ndopinionmd",
        "postgresql://localhost/2ndopinionmd"
    ]
    
    for url in fallbacks:
        try:
            conn = psycopg2.connect(url)
            conn.close()
            print(f"Using database URL: {url}")
            return url
        except Exception as e:
            print(f"Failed to connect with {url}: {e}")
            continue
    
    raise ValueError("Could not connect to database with any fallback URL")

DDL_SQL = """
CREATE SCHEMA IF NOT EXISTS ontology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ICD-10-CM mapping table (missing from base schema)
CREATE TABLE IF NOT EXISTS ontology.snomed_map_icd10cm (
  id SERIAL PRIMARY KEY,
  concept_id BIGINT,
  map_group SMALLINT,
  map_priority SMALLINT,
  map_target TEXT,
  map_category_id BIGINT,
  active BOOLEAN,
  effective_time DATE,
  refset_id BIGINT,
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(concept_id, map_group, map_priority)
);
CREATE INDEX IF NOT EXISTS snomed_map_icd10cm_concept_idx ON ontology.snomed_map_icd10cm (concept_id);
CREATE INDEX IF NOT EXISTS snomed_map_icd10cm_target_idx ON ontology.snomed_map_icd10cm (map_target);
"""

def find_rf2_files(root_dir: str) -> Dict[str, str]:
    """Find RF2 files in SNOMED CT directory structure"""
    files = {}
    
    if not os.path.exists(root_dir):
        print(f"Warning: SNOMED data directory not found: {root_dir}")
        return files
    
    for root, dirs, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.startswith('sct2_Concept_Snapshot_US1000124_'):
                files['concept'] = os.path.join(root, filename)
            elif filename.startswith('sct2_Description_Snapshot-en_US1000124_'):
                files['description'] = os.path.join(root, filename)
            elif filename.startswith('sct2_Relationship_Snapshot_US1000124_'):
                files['relationship'] = os.path.join(root, filename)
            elif filename.startswith('der2_cRefset_LanguageSnapshot-en_US1000124_'):
                files['langrefset'] = os.path.join(root, filename)
            elif filename.startswith('der2_iisssccRefset_ExtendedMapSnapshot_US1000124_'):
                files['icd10cm_map'] = os.path.join(root, filename)
    
    return files

def load_concepts(cur, file_path: str, dry_run: bool = False, target_prefix: str = ""):
    """Load SNOMED CT concepts with upsert logic"""
    table_name = f"ontology.concepts{target_prefix}"
    print(f"Loading concepts from {file_path} into {table_name}...")
    start_time = time.time()
    
    if dry_run:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            count = sum(1 for _ in reader)
        print(f"DRY RUN: Would load {count} concepts into {table_name}")
        return
    
    cur.execute("""CREATE TEMP TABLE t_concepts (
        id TEXT,
        effectiveTime TEXT,
        active TEXT,
        moduleId TEXT,
        definitionStatusId TEXT
    )""")
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        cur.copy_expert(
            "COPY t_concepts (id, effectiveTime, active, moduleId, definitionStatusId) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\\t')",
            f
        )
    
    cur.execute(f"""
        INSERT INTO {table_name} AS dst
        (concept_id, effective_time, active, module_id, definition_status)
        SELECT 
            id::BIGINT,
            TO_DATE(effectiveTime, 'YYYYMMDD'),
            active::BOOLEAN,
            moduleId::BIGINT,
            definitionStatusId::BIGINT
        FROM t_concepts
        WHERE id ~ '^[0-9]+$' AND effectiveTime ~ '^[0-9]{{8}}$'
        ON CONFLICT (concept_id) DO UPDATE SET
            effective_time=EXCLUDED.effective_time,
            active=EXCLUDED.active,
            module_id=EXCLUDED.module_id,
            definition_status=EXCLUDED.definition_status;
    """)
    
    duration = time.time() - start_time
    cur.execute("SELECT COUNT(*) FROM t_concepts")
    count = cur.fetchone()[0]
    print(f"Loaded {count} concepts in {duration:.2f}s")

def load_descriptions(cur, file_path: str, dry_run: bool = False, target_prefix: str = ""):
    """Load SNOMED CT descriptions with upsert logic"""
    table_name = f"ontology.descriptions{target_prefix}"
    print(f"Loading descriptions from {file_path} into {table_name}...")
    start_time = time.time()
    
    if dry_run:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            count = sum(1 for _ in reader)
        print(f"DRY RUN: Would load {count} descriptions into {table_name}")
        return
    
    cur.execute("""CREATE TEMP TABLE t_descriptions (
        id TEXT,
        effectiveTime TEXT,
        active TEXT,
        moduleId TEXT,
        conceptId TEXT,
        languageCode TEXT,
        typeId TEXT,
        term TEXT,
        caseSignificanceId TEXT
    )""")
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        cur.copy_expert(
            "COPY t_descriptions (id, effectiveTime, active, moduleId, conceptId, languageCode, typeId, term, caseSignificanceId) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\\t')",
            f
        )
    
    cur.execute(f"""
        INSERT INTO {table_name} AS dst
        (description_id, effective_time, active, module_id, concept_id, language_code, type_id, term, case_significance)
        SELECT 
            id::BIGINT,
            TO_DATE(effectiveTime, 'YYYYMMDD'),
            active::BOOLEAN,
            moduleId::BIGINT,
            conceptId::BIGINT,
            languageCode,
            typeId::BIGINT,
            term,
            caseSignificanceId::BIGINT
        FROM t_descriptions
        WHERE id ~ '^[0-9]+$' AND conceptId ~ '^[0-9]+$' AND effectiveTime ~ '^[0-9]{{8}}$'
        ON CONFLICT (description_id) DO UPDATE SET
            effective_time=EXCLUDED.effective_time,
            active=EXCLUDED.active,
            module_id=EXCLUDED.module_id,
            concept_id=EXCLUDED.concept_id,
            language_code=EXCLUDED.language_code,
            type_id=EXCLUDED.type_id,
            term=EXCLUDED.term,
            case_significance=EXCLUDED.case_significance;
    """)
    
    duration = time.time() - start_time
    cur.execute("SELECT COUNT(*) FROM t_descriptions")
    count = cur.fetchone()[0]
    print(f"Loaded {count} descriptions in {duration:.2f}s")

def load_relationships(cur, file_path: str, dry_run: bool = False, target_prefix: str = ""):
    """Load SNOMED CT relationships with upsert logic"""
    table_name = f"ontology.relationships{target_prefix}"
    print(f"Loading relationships from {file_path} into {table_name}...")
    start_time = time.time()
    
    if dry_run:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            count = sum(1 for _ in reader)
        print(f"DRY RUN: Would load {count} relationships into {table_name}")
        return
    
    cur.execute("""CREATE TEMP TABLE t_relationships (
        id TEXT,
        effectiveTime TEXT,
        active TEXT,
        moduleId TEXT,
        sourceId TEXT,
        destinationId TEXT,
        relationshipGroup TEXT,
        typeId TEXT,
        characteristicTypeId TEXT,
        modifierId TEXT
    )""")
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        cur.copy_expert(
            "COPY t_relationships (id, effectiveTime, active, moduleId, sourceId, destinationId, relationshipGroup, typeId, characteristicTypeId, modifierId) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\\t')",
            f
        )
    
    cur.execute(f"""
        INSERT INTO {table_name} AS dst
        (relationship_id, effective_time, active, module_id, source_id, destination_id, relationship_group, type_id, characteristic_type_id, modifier_id)
        SELECT 
            id::BIGINT,
            TO_DATE(effectiveTime, 'YYYYMMDD'),
            active::BOOLEAN,
            moduleId::BIGINT,
            sourceId::BIGINT,
            destinationId::BIGINT,
            relationshipGroup::SMALLINT,
            typeId::BIGINT,
            characteristicTypeId::BIGINT,
            modifierId::BIGINT
        FROM t_relationships
        WHERE id ~ '^[0-9]+$' AND sourceId ~ '^[0-9]+$' AND destinationId ~ '^[0-9]+$' AND effectiveTime ~ '^[0-9]{{8}}$'
        ON CONFLICT (relationship_id) DO UPDATE SET
            effective_time=EXCLUDED.effective_time,
            active=EXCLUDED.active,
            module_id=EXCLUDED.module_id,
            source_id=EXCLUDED.source_id,
            destination_id=EXCLUDED.destination_id,
            relationship_group=EXCLUDED.relationship_group,
            type_id=EXCLUDED.type_id,
            characteristic_type_id=EXCLUDED.characteristic_type_id,
            modifier_id=EXCLUDED.modifier_id;
    """)
    
    duration = time.time() - start_time
    cur.execute("SELECT COUNT(*) FROM t_relationships")
    count = cur.fetchone()[0]
    print(f"Loaded {count} relationships in {duration:.2f}s")

def load_langrefset(cur, file_path: str, dry_run: bool = False, target_prefix: str = ""):
    """Load SNOMED CT language reference set with upsert logic"""
    table_name = f"ontology.refset_members{target_prefix}"
    print(f"Loading language refset from {file_path} into {table_name}...")
    start_time = time.time()
    
    if dry_run:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            count = sum(1 for _ in reader)
        print(f"DRY RUN: Would load {count} language refset members into {table_name}")
        return
    
    cur.execute("""CREATE TEMP TABLE t_langrefset (
        id TEXT,
        effectiveTime TEXT,
        active TEXT,
        moduleId TEXT,
        refsetId TEXT,
        referencedComponentId TEXT,
        acceptabilityId TEXT
    )""")
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        cur.copy_expert(
            "COPY t_langrefset (id, effectiveTime, active, moduleId, refsetId, referencedComponentId, acceptabilityId) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\\t')",
            f
        )
    
    cur.execute(f"""
        INSERT INTO {table_name} AS dst
        (member_id, effective_time, active, module_id, refset_id, referenced_component_id, value_id)
        SELECT 
            id::BIGINT,
            TO_DATE(effectiveTime, 'YYYYMMDD'),
            active::BOOLEAN,
            moduleId::BIGINT,
            refsetId::BIGINT,
            referencedComponentId::BIGINT,
            acceptabilityId::BIGINT
        FROM t_langrefset
        WHERE id ~ '^[0-9]+$' AND refsetId ~ '^[0-9]+$' AND referencedComponentId ~ '^[0-9]+$' AND effectiveTime ~ '^[0-9]{{8}}$'
        ON CONFLICT (member_id) DO UPDATE SET
            effective_time=EXCLUDED.effective_time,
            active=EXCLUDED.active,
            module_id=EXCLUDED.module_id,
            refset_id=EXCLUDED.refset_id,
            referenced_component_id=EXCLUDED.referenced_component_id,
            value_id=EXCLUDED.value_id;
    """)
    
    duration = time.time() - start_time
    cur.execute("SELECT COUNT(*) FROM t_langrefset")
    count = cur.fetchone()[0]
    print(f"Loaded {count} language refset members in {duration:.2f}s")

def load_icd10cm_map(cur, file_path: str, dry_run: bool = False, target_prefix: str = ""):
    """Load SNOMED CT to ICD-10-CM mapping with upsert logic"""
    table_name = f"ontology.snomed_map_icd10cm{target_prefix}"
    print(f"Loading ICD-10-CM mappings from {file_path} into {table_name}...")
    start_time = time.time()
    
    if dry_run:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            count = sum(1 for _ in reader)
        print(f"DRY RUN: Would load {count} ICD-10-CM mappings into {table_name}")
        return
    
    cur.execute("""CREATE TEMP TABLE t_icd10cm_map (
        id TEXT,
        effectiveTime TEXT,
        active TEXT,
        moduleId TEXT,
        refsetId TEXT,
        referencedComponentId TEXT,
        mapGroup TEXT,
        mapPriority TEXT,
        mapRule TEXT,
        mapAdvice TEXT,
        mapTarget TEXT,
        correlationId TEXT,
        mapCategoryId TEXT
    )""")
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        cur.copy_expert(
            "COPY t_icd10cm_map (id, effectiveTime, active, moduleId, refsetId, referencedComponentId, mapGroup, mapPriority, mapRule, mapAdvice, mapTarget, correlationId, mapCategoryId) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\\t')",
            f
        )
    
    cur.execute(f"""
        INSERT INTO {table_name} AS dst
        (concept_id, map_group, map_priority, map_target, map_category_id, active, effective_time, refset_id)
        SELECT 
            referencedComponentId::BIGINT,
            COALESCE(mapGroup::SMALLINT, 1),
            COALESCE(mapPriority::SMALLINT, 1),
            mapTarget,
            COALESCE(mapCategoryId::BIGINT, 447637006),
            active::BOOLEAN,
            TO_DATE(effectiveTime, 'YYYYMMDD'),
            refsetId::BIGINT
        FROM t_icd10cm_map
        WHERE referencedComponentId ~ '^[0-9]+$' AND refsetId ~ '^[0-9]+$' AND effectiveTime ~ '^[0-9]{{8}}$'
        AND refsetId = '6011000124106'
        ON CONFLICT (concept_id, map_group, map_priority) DO UPDATE SET
            map_target=EXCLUDED.map_target,
            map_category_id=EXCLUDED.map_category_id,
            active=EXCLUDED.active,
            effective_time=EXCLUDED.effective_time,
            refset_id=EXCLUDED.refset_id;
    """)
    
    duration = time.time() - start_time
    cur.execute("SELECT COUNT(*) FROM t_icd10cm_map WHERE refsetId = '6011000124106'")
    count = cur.fetchone()[0]
    print(f"Loaded {count} ICD-10-CM mappings in {duration:.2f}s")

def main():
    parser = argparse.ArgumentParser(description="Ingest SNOMED CT RF2 data")
    parser.add_argument("--root-dir", required=True, help="Root directory of SNOMED CT RF2 files")
    parser.add_argument("--target-prefix", default="", help="Suffix for target table names (e.g., '_v2')")
    parser.add_argument("--use-views", action="store_true", help="Target views instead of tables")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be loaded without making changes")
    
    args = parser.parse_args()
    
    print(f"SNOMED CT Ingestion Starting...")
    print(f"Root directory: {args.root_dir}")
    print(f"Target prefix: '{args.target_prefix}'")
    print(f"Use views: {args.use_views}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    rf2_files = find_rf2_files(args.root_dir)
    
    if not rf2_files:
        print("No RF2 files found. Expected files:")
        print("- sct2_Concept_Snapshot_US1000124_*.txt")
        print("- sct2_Description_Snapshot-en_US1000124_*.txt")
        print("- sct2_Relationship_Snapshot_US1000124_*.txt")
        print("- der2_cRefset_LanguageSnapshot-en_US1000124_*.txt")
        print("- der2_iisssccRefset_ExtendedMapSnapshot_US1000124_*.txt")
        sys.exit(1)
    
    print("Found RF2 files:")
    for file_type, file_path in rf2_files.items():
        print(f"  {file_type}: {file_path}")
    print()
    
    if args.dry_run:
        print("DRY RUN MODE - No database changes will be made")
        for file_type, file_path in rf2_files.items():
            if file_type == 'concept':
                load_concepts(None, file_path, dry_run=True, target_prefix=args.target_prefix)
            elif file_type == 'description':
                load_descriptions(None, file_path, dry_run=True, target_prefix=args.target_prefix)
            elif file_type == 'relationship':
                load_relationships(None, file_path, dry_run=True, target_prefix=args.target_prefix)
            elif file_type == 'langrefset':
                load_langrefset(None, file_path, dry_run=True, target_prefix=args.target_prefix)
            elif file_type == 'icd10cm_map':
                load_icd10cm_map(None, file_path, dry_run=True, target_prefix=args.target_prefix)
        return
    
    database_url = get_database_url()
    print(f"Connecting to database...")
    
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            print("Setting up schema and tables...")
            cur.execute(DDL_SQL)
            conn.commit()
            
            # Load in correct order: concepts first, then descriptions, then relationships
            load_order = ['concept', 'description', 'relationship', 'langrefset', 'icd10cm_map']
            
            for file_type in load_order:
                if file_type not in rf2_files:
                    continue
                    
                file_path = rf2_files[file_type]
                try:
                    if file_type == 'concept':
                        load_concepts(cur, file_path, target_prefix=args.target_prefix)
                    elif file_type == 'description':
                        load_descriptions(cur, file_path, target_prefix=args.target_prefix)
                    elif file_type == 'relationship':
                        load_relationships(cur, file_path, target_prefix=args.target_prefix)
                    elif file_type == 'langrefset':
                        load_langrefset(cur, file_path, target_prefix=args.target_prefix)
                    elif file_type == 'icd10cm_map':
                        load_icd10cm_map(cur, file_path, target_prefix=args.target_prefix)
                    
                    conn.commit()
                    print(f"✓ Successfully loaded {file_type}")
                    
                except Exception as e:
                    print(f"✗ Error loading {file_type}: {e}")
                    conn.rollback()
                    continue
    
    print("\nSNOMED CT ingestion completed!")

if __name__ == "__main__":
    main()
