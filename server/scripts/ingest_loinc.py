#!/usr/bin/env python3
"""
LOINC Data Ingestion Script

Loads LOINC data from ZIP file into PostgreSQL ontology schema.
Supports both local ZIP files and hosted URLs with idempotent upserts.
"""

import argparse
import csv
import io
import os
import sys
import zipfile
import tempfile
import hashlib
import time
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

def get_database_url() -> str:
    """Get database URL from environment with fallbacks"""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if "+asyncpg" in database_url:
            database_url = database_url.replace("+asyncpg", "")
        return database_url
    
    fallbacks = [
        "postgresql:///2ndopinionmd",
        "postgresql://localhost/2ndopinionmd"
    ]
    
    for url in fallbacks:
        try:
            conn = psycopg2.connect(url)
            conn.close()
            print(f"Using fallback database URL: {url}")
            return url
        except:
            continue
    
    raise ValueError("Could not connect to database. Please set DATABASE_URL in .env")

DDL_SQL = """
CREATE SCHEMA IF NOT EXISTS ontology;

-- 1) Core terms
CREATE TABLE IF NOT EXISTS ontology.loinc_terms (
  loinc_num TEXT PRIMARY KEY,
  component TEXT,
  property TEXT,
  time_aspct TEXT,
  system TEXT,
  scale_typ TEXT,
  method_typ TEXT,
  class TEXT,
  classtype INT,
  long_common_name TEXT,
  shortname TEXT,
  external_copyright_notice TEXT,
  status TEXT,
  version_first_released TEXT,
  version_last_changed TEXT,
  src_version TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS loinc_terms_component_system_idx ON ontology.loinc_terms (component, system);
CREATE INDEX IF NOT EXISTS loinc_terms_class_idx ON ontology.loinc_terms (class);

-- 2) Panels
CREATE TABLE IF NOT EXISTS ontology.loinc_panels (
  parent_loinc TEXT NOT NULL,
  child_loinc TEXT NOT NULL,
  sequence INT,
  display_text TEXT,
  observation_required TEXT,
  PRIMARY KEY (parent_loinc, child_loinc)
);
CREATE INDEX IF NOT EXISTS loinc_panels_parent_idx ON ontology.loinc_panels (parent_loinc);

-- 3) Answer lists
CREATE TABLE IF NOT EXISTS ontology.loinc_answer_list (
  answer_list_id TEXT PRIMARY KEY,
  answer_list_name TEXT,
  answer_list_oid TEXT,
  ext_defined_yn TEXT
);

CREATE TABLE IF NOT EXISTS ontology.loinc_answer_link (
  loinc_num TEXT NOT NULL,
  answer_list_id TEXT NOT NULL,
  link_type TEXT,
  applicable_context TEXT,
  PRIMARY KEY (loinc_num, answer_list_id)
);

-- 4) Parts & links
CREATE TABLE IF NOT EXISTS ontology.loinc_parts (
  part_number TEXT PRIMARY KEY,
  part_type_name TEXT,
  part_name TEXT,
  part_display_name TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS ontology.loinc_part_link (
  loinc_num TEXT NOT NULL,
  part_number TEXT NOT NULL,
  part_name TEXT,
  part_code_system TEXT,
  part_type_name TEXT NOT NULL,
  PRIMARY KEY (loinc_num, part_number, part_type_name)
);
"""

def download_zip(url: str, temp_dir: str) -> str:
    """Download ZIP file from URL to temporary directory"""
    print(f"Downloading LOINC ZIP from {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    zip_path = os.path.join(temp_dir, "loinc.zip")
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Downloaded to {zip_path}")
    return zip_path

def unzip_file(zip_path: str) -> tuple[str, str]:
    """Unzip file and return extraction directory and MD5 hash"""
    with open(zip_path, 'rb') as f:
        zip_md5 = hashlib.md5(f.read()).hexdigest()
    
    extract_dir = tempfile.mkdtemp(prefix="loinc_")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)
    
    print(f"Extracted to {extract_dir} (MD5: {zip_md5})")
    return extract_dir, zip_md5

def find_csv_path(extract_dir: str, relative_path: str) -> str:
    """Find CSV file path, handling case variations"""
    full_path = os.path.join(extract_dir, relative_path)
    if os.path.exists(full_path):
        return full_path
    
    parts = relative_path.split('/')
    current_dir = extract_dir
    
    for part in parts:
        found = False
        if os.path.isdir(current_dir):
            for item in os.listdir(current_dir):
                if item.lower() == part.lower():
                    current_dir = os.path.join(current_dir, item)
                    found = True
                    break
        if not found:
            raise FileNotFoundError(f"Could not find {relative_path} in {extract_dir}")
    
    return current_dir

def get_src_version(core_csv_path: str) -> str:
    """Extract src_version from VersionLastChanged column"""
    max_version = None
    with open(core_csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            version = row.get('VersionLastChanged', '').strip()
            if version and (max_version is None or version > max_version):
                max_version = version
    
    return max_version or "unknown"

def copy_csv_to_temp_table(cur, temp_table: str, columns: List[str], csv_path: str):
    """Copy CSV data to temporary table using COPY command"""
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        cur.copy_expert(
            f"""COPY {temp_table} ({", ".join(columns)}) FROM STDIN WITH (FORMAT csv, HEADER true, QUOTE '"', ESCAPE '\\')""",
            f
        )

def load_loinc_terms(cur, csv_path: str, src_version: str, dry_run: bool = False):
    """Load LOINC terms with upsert logic"""
    print("Loading LOINC terms...")
    start_time = time.time()
    
    cur.execute("CREATE TEMP TABLE t_loinc_terms (LIKE ontology.loinc_terms INCLUDING ALL)")
    cur.execute("ALTER TABLE t_loinc_terms DROP COLUMN IF EXISTS src_version")
    cur.execute("ALTER TABLE t_loinc_terms DROP COLUMN IF EXISTS ingested_at")
    
    columns = [
        "loinc_num", "component", "property", "time_aspct", "system", "scale_typ", 
        "method_typ", "class", "classtype", "long_common_name", "shortname", 
        "external_copyright_notice", "status", "version_first_released", "version_last_changed"
    ]
    copy_csv_to_temp_table(cur, "t_loinc_terms", columns, csv_path)
    
    cur.execute("SELECT COUNT(*) FROM t_loinc_terms")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO ontology.loinc_terms AS dst
        (loinc_num, component, property, time_aspct, system, scale_typ, method_typ, class, classtype,
         long_common_name, shortname, external_copyright_notice, status, version_first_released,
         version_last_changed, src_version)
        SELECT loinc_num, component, property, time_aspct, system, scale_typ, method_typ, class, 
               NULLIF(classtype, '')::INT, long_common_name, shortname, external_copyright_notice, 
               status, version_first_released, version_last_changed, %s
        FROM t_loinc_terms
        ON CONFLICT (loinc_num) DO UPDATE SET
          component=EXCLUDED.component,
          property=EXCLUDED.property,
          time_aspct=EXCLUDED.time_aspct,
          system=EXCLUDED.system,
          scale_typ=EXCLUDED.scale_typ,
          method_typ=EXCLUDED.method_typ,
          class=EXCLUDED.class,
          classtype=EXCLUDED.classtype,
          long_common_name=EXCLUDED.long_common_name,
          shortname=EXCLUDED.shortname,
          external_copyright_notice=EXCLUDED.external_copyright_notice,
          status=EXCLUDED.status,
          version_first_released=EXCLUDED.version_first_released,
          version_last_changed=EXCLUDED.version_last_changed,
          src_version=EXCLUDED.src_version;
    """, (src_version,))
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC terms in {duration:.2f}s")

def load_loinc_panels(cur, csv_path: str, dry_run: bool = False):
    """Load LOINC panels with upsert logic"""
    print("Loading LOINC panels...")
    start_time = time.time()
    
    cur.execute("CREATE TEMP TABLE t_panels (LIKE ontology.loinc_panels INCLUDING ALL)")
    
    columns = ["parent_loinc", "child_loinc", "sequence", "display_text", "observation_required"]
    copy_csv_to_temp_table(cur, "t_panels", columns, csv_path)
    
    cur.execute("DELETE FROM t_panels WHERE child_loinc IS NULL OR child_loinc = ''")
    
    cur.execute("SELECT COUNT(*) FROM t_panels")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO ontology.loinc_panels AS dst
        (parent_loinc, child_loinc, sequence, display_text, observation_required)
        SELECT parent_loinc, child_loinc, NULLIF(sequence, '')::INT, display_text, observation_required
        FROM t_panels
        ON CONFLICT (parent_loinc, child_loinc) DO UPDATE SET
          sequence=EXCLUDED.sequence,
          display_text=EXCLUDED.display_text,
          observation_required=EXCLUDED.observation_required;
    """)
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC panels in {duration:.2f}s")

def load_answer_lists(cur, csv_path: str, dry_run: bool = False):
    """Load LOINC answer lists with upsert logic"""
    print("Loading LOINC answer lists...")
    start_time = time.time()
    
    cur.execute("CREATE TEMP TABLE t_answer_list (LIKE ontology.loinc_answer_list INCLUDING ALL)")
    
    columns = ["answer_list_id", "answer_list_name", "answer_list_oid", "ext_defined_yn"]
    copy_csv_to_temp_table(cur, "t_answer_list", columns, csv_path)
    
    cur.execute("SELECT COUNT(*) FROM t_answer_list")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO ontology.loinc_answer_list AS dst
        SELECT * FROM t_answer_list
        ON CONFLICT (answer_list_id) DO UPDATE SET
          answer_list_name=EXCLUDED.answer_list_name,
          answer_list_oid=EXCLUDED.answer_list_oid,
          ext_defined_yn=EXCLUDED.ext_defined_yn;
    """)
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC answer lists in {duration:.2f}s")

def load_answer_links(cur, csv_path: str, dry_run: bool = False):
    """Load LOINC answer links with upsert logic"""
    print("Loading LOINC answer links...")
    start_time = time.time()
    
    cur.execute("CREATE TEMP TABLE t_answer_link (LIKE ontology.loinc_answer_link INCLUDING ALL)")
    
    columns = ["loinc_num", "answer_list_id", "link_type", "applicable_context"]
    copy_csv_to_temp_table(cur, "t_answer_link", columns, csv_path)
    
    cur.execute("SELECT COUNT(*) FROM t_answer_link")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO ontology.loinc_answer_link AS dst
        SELECT * FROM t_answer_link
        ON CONFLICT (loinc_num, answer_list_id) DO UPDATE SET
          link_type=EXCLUDED.link_type,
          applicable_context=EXCLUDED.applicable_context;
    """)
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC answer links in {duration:.2f}s")

def load_parts(cur, csv_path: str, dry_run: bool = False):
    """Load LOINC parts with upsert logic"""
    print("Loading LOINC parts...")
    start_time = time.time()
    
    cur.execute("CREATE TEMP TABLE t_parts (LIKE ontology.loinc_parts INCLUDING ALL)")
    
    columns = ["part_number", "part_type_name", "part_name", "part_display_name", "status"]
    copy_csv_to_temp_table(cur, "t_parts", columns, csv_path)
    
    cur.execute("SELECT COUNT(*) FROM t_parts")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO ontology.loinc_parts AS dst
        SELECT * FROM t_parts
        ON CONFLICT (part_number) DO UPDATE SET
          part_type_name=EXCLUDED.part_type_name,
          part_name=EXCLUDED.part_name,
          part_display_name=EXCLUDED.part_display_name,
          status=EXCLUDED.status;
    """)
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC parts in {duration:.2f}s")

def load_part_links(cur, csv_path: str, dry_run: bool = False):
    """Load LOINC part links with upsert logic"""
    print("Loading LOINC part links...")
    start_time = time.time()
    
    cur.execute("CREATE TEMP TABLE t_part_link (LIKE ontology.loinc_part_link INCLUDING ALL)")
    
    columns = ["loinc_num", "part_number", "part_name", "part_code_system", "part_type_name"]
    copy_csv_to_temp_table(cur, "t_part_link", columns, csv_path)
    
    cur.execute("SELECT COUNT(*) FROM t_part_link")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO ontology.loinc_part_link AS dst
        SELECT * FROM t_part_link
        ON CONFLICT (loinc_num, part_number, part_type_name) DO UPDATE SET
          part_name=EXCLUDED.part_name,
          part_code_system=EXCLUDED.part_code_system;
    """)
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC part links in {duration:.2f}s")

def run_smoke_tests(cur):
    """Run smoke tests to verify data integrity"""
    print("\nRunning smoke tests...")
    
    cur.execute("SELECT loinc_num, long_common_name, system, scale_typ FROM ontology.loinc_terms WHERE loinc_num = '2345-7'")
    glucose_result = cur.fetchone()
    
    if not glucose_result:
        raise RuntimeError("SMOKE TEST FAILED: Code 2345-7 (glucose) not found in loinc_terms")
    
    print(f"✓ Found glucose code 2345-7: {glucose_result[1]}")
    
    tables = [
        "ontology.loinc_terms",
        "ontology.loinc_panels", 
        "ontology.loinc_answer_list",
        "ontology.loinc_answer_link",
        "ontology.loinc_parts",
        "ontology.loinc_part_link"
    ]
    
    print("\nTable counts:")
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count:,} rows")

def main():
    parser = argparse.ArgumentParser(description="Ingest LOINC data into PostgreSQL")
    parser.add_argument("--zip", help="Path to local LOINC ZIP file")
    parser.add_argument("--zip-url", help="URL to download LOINC ZIP file")
    parser.add_argument("--schema", default="ontology", help="Database schema (default: ontology)")
    parser.add_argument("--dry-run", action="store_true", help="Run without committing changes")
    
    args = parser.parse_args()
    
    if not args.zip and not args.zip_url:
        parser.error("Must specify either --zip or --zip-url")
    
    if args.zip and args.zip_url:
        parser.error("Cannot specify both --zip and --zip-url")
    
    temp_dir = None
    try:
        if args.zip_url:
            temp_dir = tempfile.mkdtemp(prefix="loinc_download_")
            zip_path = download_zip(args.zip_url, temp_dir)
        else:
            zip_path = args.zip
            if not os.path.exists(zip_path):
                raise FileNotFoundError(f"ZIP file not found: {zip_path}")
        
        extract_dir, zip_md5 = unzip_file(zip_path)
        print(f"ZIP MD5: {zip_md5}")
        
        csv_files = {
            'core': find_csv_path(extract_dir, "LoincTableCore/LoincTableCore.csv"),
            'panels': find_csv_path(extract_dir, "AccessoryFiles/PanelsAndForms/PanelsAndForms.csv"),
            'answer_list': find_csv_path(extract_dir, "AccessoryFiles/AnswerFile/AnswerList.csv"),
            'answer_link': find_csv_path(extract_dir, "AccessoryFiles/AnswerFile/LoincAnswerListLink.csv"),
            'parts': find_csv_path(extract_dir, "AccessoryFiles/PartFile/Part.csv"),
            'part_link': find_csv_path(extract_dir, "AccessoryFiles/PartFile/LoincPartLink_Primary.csv")
        }
        
        src_version = get_src_version(csv_files['core'])
        print(f"Source version: {src_version}")
        
        database_url = get_database_url()
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        
        try:
            with conn.cursor() as cur:
                print("Creating schema and tables...")
                cur.execute(DDL_SQL)
                
                load_loinc_terms(cur, csv_files['core'], src_version, args.dry_run)
                load_loinc_panels(cur, csv_files['panels'], args.dry_run)
                load_answer_lists(cur, csv_files['answer_list'], args.dry_run)
                load_answer_links(cur, csv_files['answer_link'], args.dry_run)
                load_parts(cur, csv_files['parts'], args.dry_run)
                load_part_links(cur, csv_files['part_link'], args.dry_run)
                
                run_smoke_tests(cur)
                
                if args.dry_run:
                    conn.rollback()
                    print("\n🔄 DRY RUN: All changes rolled back")
                else:
                    conn.commit()
                    print("\n✅ All data committed successfully")
                    
        finally:
            conn.close()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
