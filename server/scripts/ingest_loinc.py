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

def _row_pick(d: dict, candidates):
    """Pick first non-empty field from candidates (case-insensitive match)."""
    if not d:
        return ''
    # normalize keys for robust access
    lower = {k.lower(): v for k, v in d.items()}
    for c in candidates:
        v = lower.get(c.lower())
        if v is not None and str(v).strip() != '':
            return str(v).strip()
    return ''

def _batch_insert(cur, table, cols, rows, page=2000):
    """Insert rows in batches using psycopg2.extras.execute_values."""
    from psycopg2.extras import execute_values
    for i in range(0, len(rows), page):
        execute_values(
            cur,
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s",
            rows[i:i+page]
        )


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
    
    cur.execute("""CREATE TEMP TABLE t_loinc_terms (
  loinc_num TEXT,
  component TEXT,
  property TEXT,
  time_aspct TEXT,
  system TEXT,
  scale_typ TEXT,
  method_typ TEXT,
  class TEXT,
  classtype TEXT,
  long_common_name TEXT,
  shortname TEXT,
  external_copyright_notice TEXT,
  status TEXT,
  version_first_released TEXT,
  version_last_changed TEXT
)""")
    
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
    """Load LOINC panels with upsert logic (robust to wide CSVs)."""
    print("Loading LOINC panels...")
    import csv, time
    start_time = time.time()

    # Stage table with TEXT columns only
    cur.execute("""CREATE TEMP TABLE t_panels (
      parent_loinc TEXT,
      child_loinc TEXT,
      sequence TEXT,
      display_text TEXT,
      observation_required TEXT
    )""")

    # Read only the columns we need using DictReader
    needed = ["parent_loinc","child_loinc","sequence","display_text","observation_required"]
    parent_keys = ["ParentLoinc","Parent LOINC","PARENTLOINC","PanelLoinc","Panel LOINC","ParentLOINCNumber","ParentID"]
    child_keys  = ["Loinc","LOINC","ChildLoinc","Child LOINC","ChildLOINCNumber"]
    seq_keys    = ["Sequence","SEQUENCE","ChildSequence","ItemSequenceNumber","Item Sequence"]
    disp_keys   = ["DisplayNameForForm","Display Name For Form","FORMDISPNM","FORMDISP","DisplayName"]
    req_keys    = ["ObservationRequiredInPanel","Required","OBSERVATIONREQUIREDINPANEL","Observation Required In Panel","REQUIRED"]

    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            parent = _row_pick(row, parent_keys)
            child  = _row_pick(row, child_keys)
            if not child:
                continue
            seq    = _row_pick(row, seq_keys)
            disp   = _row_pick(row, disp_keys)
            req    = _row_pick(row, req_keys)
            rows.append((parent, child, seq, disp, req))

    if rows:
        _batch_insert(cur, "t_panels", needed, rows)

    # Clean and upsert
    cur.execute("DELETE FROM t_panels WHERE child_loinc IS NULL OR child_loinc = ''")
    cur.execute("SELECT COUNT(*) FROM t_panels")
    temp_count = cur.fetchone()[0]

    cur.execute("""
        WITH ranked AS (
          SELECT
            parent_loinc,
            child_loinc,
            sequence,
            display_text,
            observation_required,
            ROW_NUMBER() OVER (
              PARTITION BY parent_loinc, child_loinc
              ORDER BY NULLIF(sequence,'')::INT NULLS LAST, display_text NULLS LAST
            ) AS rn
          FROM t_panels
        )
        INSERT INTO ontology.loinc_panels AS dst
          (parent_loinc, child_loinc, sequence, display_text, observation_required)
        SELECT
          parent_loinc,
          child_loinc,
          NULLIF(sequence, '')::INT,
          display_text,
          observation_required
        FROM ranked
        WHERE rn = 1
        ON CONFLICT (parent_loinc, child_loinc) DO UPDATE SET
          sequence=EXCLUDED.sequence,
          display_text=EXCLUDED.display_text,
          observation_required=EXCLUDED.observation_required;
    """)

    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC panels in {duration:.2f}s")


def load_answer_lists(cur, csv_path: str, dry_run: bool = False):
    """Load LOINC answer lists (robust to column variations)."""
    print("Loading LOINC answer lists...")
    import csv, time
    start_time = time.time()

    cur.execute("""CREATE TEMP TABLE t_answer_list (
      answer_list_id TEXT,
      answer_list_name TEXT,
      answer_list_oid TEXT,
      ext_defined_yn TEXT
    )""")

    id_keys   = ["AnswerListId","AnswerListID","LISTID","ListId"]
    name_keys = ["AnswerListName","Answer List Name","LISTNAME","ListName"]
    oid_keys  = ["AnswerListOid","AnswerListOID","LISTOID","ListOID"]
    ext_keys  = ["ExtDefinedYn","ExtDefinedYN","ExternallyDefined","Externally Defined","ExtDefined"]

    rows=[]
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid  = _row_pick(row, id_keys)
            if not rid:  # require id
                continue
            rnm  = _row_pick(row, name_keys)
            roid = _row_pick(row, oid_keys)
            ext  = _row_pick(row, ext_keys)
            rows.append((rid, rnm, roid, ext))

    if rows:
        _batch_insert(cur, "t_answer_list", ["answer_list_id","answer_list_name","answer_list_oid","ext_defined_yn"], rows)

    cur.execute("SELECT COUNT(*) FROM t_answer_list")
    temp_count = cur.fetchone()[0]

    cur.execute("""
WITH ranked AS (
  SELECT
    answer_list_id,
    answer_list_name,
    answer_list_oid,
    ext_defined_yn,
    ROW_NUMBER() OVER (
      PARTITION BY answer_list_id
      ORDER BY answer_list_name NULLS LAST, answer_list_oid NULLS LAST
    ) AS rn
  FROM t_answer_list
  WHERE answer_list_id IS NOT NULL AND answer_list_id <> ''
)
INSERT INTO ontology.loinc_answer_list AS dst
  (answer_list_id, answer_list_name, answer_list_oid, ext_defined_yn)
SELECT
  answer_list_id, answer_list_name, answer_list_oid, ext_defined_yn
FROM ranked
WHERE rn = 1
ON CONFLICT (answer_list_id) DO UPDATE SET
  answer_list_name=EXCLUDED.answer_list_name,
  answer_list_oid=EXCLUDED.answer_list_oid,
  ext_defined_yn=EXCLUDED.ext_defined_yn;
""")

    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC answer lists in {duration:.2f}s")


def load_answer_links(cur, csv_path: str, dry_run: bool = False):
    """Load LOINC answer links (robust to column variations)."""
    print("Loading LOINC answer links...")
    import csv, time
    start_time = time.time()

    cur.execute("""CREATE TEMP TABLE t_answer_link (
      loinc_num TEXT,
      answer_list_id TEXT,
      link_type TEXT,
      applicable_context TEXT
    )""")

    loinc_keys = ["Loinc","LOINC","LoincNumber","LoincNum","LOINC_NUM"]
    id_keys    = ["AnswerListId","AnswerListID","LISTID","ListId"]
    type_keys  = ["LinkType","LINKTYPE","Type"]
    ctx_keys   = ["ApplicableContext","APPLICABLECONTEXT","Context"]

    rows=[]
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            loinc = _row_pick(row, loinc_keys)
            aid   = _row_pick(row, id_keys)
            if not loinc or not aid:
                continue
            ltype = _row_pick(row, type_keys)
            ctx   = _row_pick(row, ctx_keys)
            rows.append((loinc, aid, ltype, ctx))

    if rows:
        _batch_insert(cur, "t_answer_link", ["loinc_num","answer_list_id","link_type","applicable_context"], rows)

    cur.execute("SELECT COUNT(*) FROM t_answer_link")
    temp_count = cur.fetchone()[0]

    cur.execute("""
WITH ranked AS (
  SELECT
    loinc_num,
    answer_list_id,
    link_type,
    applicable_context,
    ROW_NUMBER() OVER (
      PARTITION BY loinc_num, answer_list_id
      ORDER BY link_type NULLS LAST, applicable_context NULLS LAST
    ) AS rn
  FROM t_answer_link
  WHERE loinc_num IS NOT NULL AND loinc_num <> ''
    AND answer_list_id IS NOT NULL AND answer_list_id <> ''
)
INSERT INTO ontology.loinc_answer_link AS dst
  (loinc_num, answer_list_id, link_type, applicable_context)
SELECT
  loinc_num, answer_list_id, link_type, applicable_context
FROM ranked
WHERE rn = 1
ON CONFLICT (loinc_num, answer_list_id) DO UPDATE SET
  link_type=EXCLUDED.link_type,
  applicable_context=EXCLUDED.applicable_context;
""")

    duration = time.time() - start_time
    print(f"Loaded {temp_count} LOINC answer links in {duration:.2f}s")


def load_parts(cur, csv_path: str, dry_run: bool = False):
    """Load LOINC parts (robust to column variations)."""
    print("Loading LOINC parts...")
    import csv, time
    start_time = time.time()

    cur.execute("""CREATE TEMP TABLE t_parts (
      part_number TEXT,
      part_type_name TEXT,
      part_name TEXT,
      part_display_name TEXT,
      status TEXT
    )""")

    num_keys   = ["PartNumber","PARTNUMBER","Part Num","PartNum"]
    type_keys  = ["PartTypeName","PartType","PARTTYPENAME"]
    name_keys  = ["PartName","PARTNAME","Name"]
    disp_keys  = ["PartDisplayName","Part Display Name","PARTDISPLAYNAME","DisplayName"]
    stat_keys  = ["Status","STATUS"]

    rows=[]
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pn   = _row_pick(row, num_keys)
            if not pn:
                continue
            ptyp = _row_pick(row, type_keys)
            pnam = _row_pick(row, name_keys)
            pdis = _row_pick(row, disp_keys)
            stat = _row_pick(row, stat_keys)
            rows.append((pn, ptyp, pnam, pdis, stat))

    if rows:
        _batch_insert(cur, "t_parts", ["part_number","part_type_name","part_name","part_display_name","status"], rows)

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
    """Load LOINC part links (robust to column variations)."""
    print("Loading LOINC part links...")
    import csv, time
    start_time = time.time()

    cur.execute("""CREATE TEMP TABLE t_part_link (
      loinc_num TEXT,
      part_number TEXT,
      part_name TEXT,
      part_code_system TEXT,
      part_type_name TEXT
    )""")

    loinc_keys = ["LoincNumber","LOINC_NUM","LOINC","Loinc"]
    num_keys   = ["PartNumber","PARTNUMBER","PartNumber (PartNumber)"]
    name_keys  = ["PartName","PARTNAME"]
    code_keys  = ["PartCodeSystem","PartCodeSys","CODE_SYSTEM","Part Code System"]
    type_keys  = ["PartTypeName","PartType","PARTTYPENAME"]

    rows=[]
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            loinc = _row_pick(row, loinc_keys)
            pn    = _row_pick(row, num_keys)
            if not loinc or not pn:
                continue
            nam   = _row_pick(row, name_keys)
            code  = _row_pick(row, code_keys)
            typ   = _row_pick(row, type_keys)
            rows.append((loinc, pn, nam, code, typ))

    if rows:
        _batch_insert(cur, "t_part_link", ["loinc_num","part_number","part_name","part_code_system","part_type_name"], rows)

    cur.execute("SELECT COUNT(*) FROM t_part_link")
    temp_count = cur.fetchone()[0]

    cur.execute("""
WITH ranked AS (
  SELECT
    loinc_num,
    part_number,
    part_name,
    part_code_system,
    part_type_name,
    ROW_NUMBER() OVER (
      PARTITION BY loinc_num, part_number, part_type_name
      ORDER BY part_name NULLS LAST, part_code_system NULLS LAST
    ) AS rn
  FROM t_part_link
  WHERE loinc_num IS NOT NULL AND loinc_num <> ''
    AND part_number IS NOT NULL AND part_number <> ''
    AND part_type_name IS NOT NULL AND part_type_name <> ''
)
INSERT INTO ontology.loinc_part_link AS dst
  (loinc_num, part_number, part_name, part_code_system, part_type_name)
SELECT
  loinc_num, part_number, part_name, part_code_system, part_type_name
FROM ranked
WHERE rn = 1
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
