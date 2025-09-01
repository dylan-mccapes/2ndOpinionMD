#!/usr/bin/env python3
"""
RxNorm Data Ingestion Script

Loads RxNorm data from ZIP file into PostgreSQL ontology schema.
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
import re
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

-- Enable pg_trgm extension for fast text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- A. RXNCONSO → ontology.rxnorm_conso
CREATE TABLE IF NOT EXISTS ontology.rxnorm_conso (
  rxcui TEXT,
  lat TEXT,
  ts TEXT,
  lui TEXT,
  stt TEXT,
  sui TEXT,
  ispref TEXT,
  rxaui TEXT PRIMARY KEY,
  saui TEXT,
  scui TEXT,
  sdui TEXT,
  sab TEXT,
  tty TEXT,
  code TEXT,
  str TEXT,
  srl TEXT,
  suppress TEXT,
  cvf TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast search and filtering
CREATE INDEX IF NOT EXISTS rxnorm_conso_rxcui_idx ON ontology.rxnorm_conso (rxcui);
CREATE INDEX IF NOT EXISTS rxnorm_conso_tty_str_idx ON ontology.rxnorm_conso (tty, str);
CREATE INDEX IF NOT EXISTS rxnorm_conso_str_gin_idx ON ontology.rxnorm_conso USING gin (str gin_trgm_ops);

-- B. RXNREL → ontology.rxnorm_rel
CREATE TABLE IF NOT EXISTS ontology.rxnorm_rel (
  rxcui1 TEXT,
  rxaui1 TEXT,
  stype1 TEXT,
  rel TEXT,
  rxcui2 TEXT,
  rxaui2 TEXT,
  stype2 TEXT,
  rela TEXT,
  rui TEXT PRIMARY KEY,
  srui TEXT,
  sab TEXT,
  sl TEXT,
  rg TEXT,
  dir TEXT,
  suppress TEXT,
  cvf TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for relationship queries
CREATE INDEX IF NOT EXISTS rxnorm_rel_rxcui1_idx ON ontology.rxnorm_rel (rxcui1);
CREATE INDEX IF NOT EXISTS rxnorm_rel_rxcui2_idx ON ontology.rxnorm_rel (rxcui2);
CREATE INDEX IF NOT EXISTS rxnorm_rel_rel_idx ON ontology.rxnorm_rel (rel);
CREATE INDEX IF NOT EXISTS rxnorm_rel_rela_idx ON ontology.rxnorm_rel (rela);

-- C. RXNSAT → ontology.rxnorm_sat
CREATE TABLE IF NOT EXISTS ontology.rxnorm_sat (
  rxcui TEXT,
  lui TEXT,
  sui TEXT,
  rxaui TEXT,
  stype TEXT,
  code TEXT,
  atui TEXT PRIMARY KEY,
  satui TEXT,
  atn TEXT,
  sab TEXT,
  atv TEXT,
  suppress TEXT,
  cvf TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for attribute queries
CREATE INDEX IF NOT EXISTS rxnorm_sat_atn_idx ON ontology.rxnorm_sat (atn);
CREATE INDEX IF NOT EXISTS rxnorm_sat_ndc_idx ON ontology.rxnorm_sat (atn) WHERE atn = 'NDC';

-- D. Derived NDC map → ontology.rxnorm_ndc
CREATE TABLE IF NOT EXISTS ontology.rxnorm_ndc (
  ndc_norm TEXT,
  ndc_raw TEXT,
  rxcui TEXT,
  atui TEXT,
  sab TEXT,
  PRIMARY KEY(ndc_norm, rxcui),
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for NDC lookup
CREATE INDEX IF NOT EXISTS rxnorm_ndc_norm_idx ON ontology.rxnorm_ndc (ndc_norm);
"""

def download_zip(url: str, temp_dir: str) -> str:
    """Download ZIP file from URL to temp directory"""
    print(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    zip_path = os.path.join(temp_dir, "rxnorm.zip")
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return zip_path

def unzip_file(zip_path: str) -> tuple[str, str]:
    """Unzip file and return extract directory and MD5 hash"""
    with open(zip_path, 'rb') as f:
        zip_md5 = hashlib.md5(f.read()).hexdigest()
    
    extract_dir = tempfile.mkdtemp(prefix="rxnorm_extract_")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    return extract_dir, zip_md5

def find_rrf_path(extract_dir: str, filename: str) -> str:
    """Find RRF file path (case-insensitive search)"""
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.lower() == filename.lower():
                return os.path.join(root, file)
    
    raise FileNotFoundError(f"Could not find {filename} in extracted ZIP")

def normalize_ndc(raw_ndc: str) -> str:
    """Normalize NDC to 11-digit format"""
    digits_only = re.sub(r'[^0-9]', '', raw_ndc)
    
    if len(digits_only) < 11:
        digits_only = digits_only.zfill(11)
    elif len(digits_only) > 11:
        digits_only = digits_only[:11]
    
    return digits_only

def copy_rrf_to_temp_table(cur, temp_table: str, columns: List[str], rrf_path: str):
    """Copy RRF data to temporary table using COPY command"""
    print(f"Copying {rrf_path} to {temp_table}...")
    
    with open(rrf_path, 'r', encoding='utf-8', newline='') as f:
        cur.copy_expert(
            f"""COPY {temp_table} ({", ".join(columns)}) FROM STDIN WITH (FORMAT csv, DELIMITER '|', NULL '', QUOTE E'\\b')""",
            f
        )

def load_rxnorm_conso(cur, rrf_path: str, dry_run: bool = False):
    """Load RxNorm CONSO with upsert logic"""
    print("Loading RxNorm CONSO...")
    start_time = time.time()
    
    cur.execute("""CREATE TEMP TABLE t_rxnorm_conso (
      rxcui TEXT,
      lat TEXT,
      ts TEXT,
      lui TEXT,
      stt TEXT,
      sui TEXT,
      ispref TEXT,
      rxaui TEXT,
      saui TEXT,
      scui TEXT,
      sdui TEXT,
      sab TEXT,
      tty TEXT,
      code TEXT,
      str TEXT,
      srl TEXT,
      suppress TEXT,
      cvf TEXT,
      extra TEXT
    )""")
    
    columns = [
        "rxcui", "lat", "ts", "lui", "stt", "sui", "ispref", "rxaui",
        "saui", "scui", "sdui", "sab", "tty", "code", "str", "srl", 
        "suppress", "cvf", "extra"
    ]
    copy_rrf_to_temp_table(cur, "t_rxnorm_conso", columns, rrf_path)
    
    cur.execute("SELECT COUNT(*) FROM t_rxnorm_conso")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        WITH ranked AS (
          SELECT rxcui, lat, ts, lui, stt, sui, ispref, rxaui, saui, scui, sdui, 
                 sab, tty, code, str, srl, suppress, cvf,
                 ROW_NUMBER() OVER (PARTITION BY rxaui ORDER BY 1) as rn
          FROM t_rxnorm_conso
        )
        INSERT INTO ontology.rxnorm_conso AS dst
        (rxcui, lat, ts, lui, stt, sui, ispref, rxaui, saui, scui, sdui,
         sab, tty, code, str, srl, suppress, cvf)
        SELECT rxcui, lat, ts, lui, stt, sui, ispref, rxaui, saui, scui, sdui,
               sab, tty, code, str, srl, suppress, cvf
        FROM ranked
        WHERE rn = 1
        ON CONFLICT (rxaui) DO UPDATE SET
          rxcui=EXCLUDED.rxcui,
          lat=EXCLUDED.lat,
          ts=EXCLUDED.ts,
          lui=EXCLUDED.lui,
          stt=EXCLUDED.stt,
          sui=EXCLUDED.sui,
          ispref=EXCLUDED.ispref,
          saui=EXCLUDED.saui,
          scui=EXCLUDED.scui,
          sdui=EXCLUDED.sdui,
          sab=EXCLUDED.sab,
          tty=EXCLUDED.tty,
          code=EXCLUDED.code,
          str=EXCLUDED.str,
          srl=EXCLUDED.srl,
          suppress=EXCLUDED.suppress,
          cvf=EXCLUDED.cvf;
    """)
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} RxNorm CONSO records in {duration:.2f}s")

def load_rxnorm_rel(cur, rrf_path: str, dry_run: bool = False):
    """Load RxNorm REL with upsert logic"""
    print("Loading RxNorm REL...")
    start_time = time.time()
    
    cur.execute("""CREATE TEMP TABLE t_rxnorm_rel (
      rxcui1 TEXT,
      rxaui1 TEXT,
      stype1 TEXT,
      rel TEXT,
      rxcui2 TEXT,
      rxaui2 TEXT,
      stype2 TEXT,
      rela TEXT,
      rui TEXT,
      srui TEXT,
      sab TEXT,
      sl TEXT,
      rg TEXT,
      dir TEXT,
      suppress TEXT,
      cvf TEXT,
      extra TEXT
    )""")
    
    columns = [
        "rxcui1", "rxaui1", "stype1", "rel", "rxcui2", "rxaui2", "stype2",
        "rela", "rui", "srui", "sab", "sl", "rg", "dir", "suppress", "cvf", "extra"
    ]
    copy_rrf_to_temp_table(cur, "t_rxnorm_rel", columns, rrf_path)
    
    cur.execute("SELECT COUNT(*) FROM t_rxnorm_rel")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        WITH ranked AS (
          SELECT rxcui1, rxaui1, stype1, rel, rxcui2, rxaui2, stype2, rela, rui,
                 srui, sab, sl, rg, dir, suppress, cvf,
                 ROW_NUMBER() OVER (PARTITION BY rui ORDER BY 1) as rn
          FROM t_rxnorm_rel
        )
        INSERT INTO ontology.rxnorm_rel AS dst
        (rxcui1, rxaui1, stype1, rel, rxcui2, rxaui2, stype2, rela, rui,
         srui, sab, sl, rg, dir, suppress, cvf)
        SELECT rxcui1, rxaui1, stype1, rel, rxcui2, rxaui2, stype2, rela, rui,
               srui, sab, sl, rg, dir, suppress, cvf
        FROM ranked
        WHERE rn = 1
        ON CONFLICT (rui) DO UPDATE SET
          rxcui1=EXCLUDED.rxcui1,
          rxaui1=EXCLUDED.rxaui1,
          stype1=EXCLUDED.stype1,
          rel=EXCLUDED.rel,
          rxcui2=EXCLUDED.rxcui2,
          rxaui2=EXCLUDED.rxaui2,
          stype2=EXCLUDED.stype2,
          rela=EXCLUDED.rela,
          srui=EXCLUDED.srui,
          sab=EXCLUDED.sab,
          sl=EXCLUDED.sl,
          rg=EXCLUDED.rg,
          dir=EXCLUDED.dir,
          suppress=EXCLUDED.suppress,
          cvf=EXCLUDED.cvf;
    """)
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} RxNorm REL records in {duration:.2f}s")

def load_rxnorm_sat(cur, rrf_path: str, dry_run: bool = False):
    """Load RxNorm SAT with upsert logic"""
    print("Loading RxNorm SAT...")
    start_time = time.time()
    
    cur.execute("""CREATE TEMP TABLE t_rxnorm_sat (
      rxcui TEXT,
      lui TEXT,
      sui TEXT,
      rxaui TEXT,
      stype TEXT,
      code TEXT,
      atui TEXT,
      satui TEXT,
      atn TEXT,
      sab TEXT,
      atv TEXT,
      suppress TEXT,
      cvf TEXT,
      extra TEXT
    )""")
    
    columns = [
        "rxcui", "lui", "sui", "rxaui", "stype", "code", "atui", "satui",
        "atn", "sab", "atv", "suppress", "cvf", "extra"
    ]
    copy_rrf_to_temp_table(cur, "t_rxnorm_sat", columns, rrf_path)
    
    cur.execute("SELECT COUNT(*) FROM t_rxnorm_sat")
    temp_count = cur.fetchone()[0]
    
    cur.execute("""
        WITH ranked AS (
          SELECT rxcui, lui, sui, rxaui, stype, code, atui, satui, atn, sab, atv,
                 suppress, cvf,
                 ROW_NUMBER() OVER (PARTITION BY atui ORDER BY 1) as rn
          FROM t_rxnorm_sat
        )
        INSERT INTO ontology.rxnorm_sat AS dst
        (rxcui, lui, sui, rxaui, stype, code, atui, satui, atn, sab, atv,
         suppress, cvf)
        SELECT rxcui, lui, sui, rxaui, stype, code, atui, satui, atn, sab, atv,
               suppress, cvf
        FROM ranked
        WHERE rn = 1
        ON CONFLICT (atui) DO UPDATE SET
          rxcui=EXCLUDED.rxcui,
          lui=EXCLUDED.lui,
          sui=EXCLUDED.sui,
          rxaui=EXCLUDED.rxaui,
          stype=EXCLUDED.stype,
          code=EXCLUDED.code,
          satui=EXCLUDED.satui,
          atn=EXCLUDED.atn,
          sab=EXCLUDED.sab,
          atv=EXCLUDED.atv,
          suppress=EXCLUDED.suppress,
          cvf=EXCLUDED.cvf;
    """)
    
    duration = time.time() - start_time
    print(f"Loaded {temp_count} RxNorm SAT records in {duration:.2f}s")

def build_ndc_map(cur, dry_run: bool = False):
    """Build NDC mapping table from SAT where ATN='NDC'"""
    print("Building NDC mapping table...")
    start_time = time.time()
    
    cur.execute("""
        WITH ndc_data AS (
          SELECT DISTINCT
            rxcui,
            atui,
            sab,
            atv as ndc_raw
          FROM ontology.rxnorm_sat
          WHERE atn = 'NDC' AND atv IS NOT NULL AND atv != ''
        ),
        normalized_ndc AS (
          SELECT 
            rxcui,
            atui,
            sab,
            ndc_raw,
            LPAD(REGEXP_REPLACE(ndc_raw, '[^0-9]', '', 'g'), 11, '0') as ndc_norm
          FROM ndc_data
          WHERE LENGTH(REGEXP_REPLACE(ndc_raw, '[^0-9]', '', 'g')) > 0
        )
        INSERT INTO ontology.rxnorm_ndc (ndc_norm, ndc_raw, rxcui, atui, sab)
        SELECT ndc_norm, ndc_raw, rxcui, atui, sab
        FROM normalized_ndc
        WHERE LENGTH(ndc_norm) = 11
        ON CONFLICT (ndc_norm, rxcui) DO UPDATE SET
          ndc_raw=EXCLUDED.ndc_raw,
          atui=EXCLUDED.atui,
          sab=EXCLUDED.sab;
    """)
    
    cur.execute("SELECT COUNT(*) FROM ontology.rxnorm_ndc")
    ndc_count = cur.fetchone()[0]
    
    duration = time.time() - start_time
    print(f"Built NDC mapping table with {ndc_count} entries in {duration:.2f}s")

def run_smoke_tests(cur):
    """Run smoke tests to verify data integrity"""
    print("\nRunning smoke tests...")
    
    cur.execute("SELECT rxcui, str FROM ontology.rxnorm_conso WHERE LOWER(str) LIKE '%ibuprofen%' LIMIT 1")
    ibuprofen_result = cur.fetchone()
    
    if not ibuprofen_result:
        raise RuntimeError("SMOKE TEST FAILED: Ibuprofen not found in rxnorm_conso")
    
    print(f"✓ Found ibuprofen: RXCUI {ibuprofen_result[0]} - {ibuprofen_result[1]}")
    
    cur.execute("SELECT rxcui, str FROM ontology.rxnorm_conso WHERE LOWER(str) LIKE '%acetaminophen%' LIMIT 1")
    acetaminophen_result = cur.fetchone()
    
    if not acetaminophen_result:
        raise RuntimeError("SMOKE TEST FAILED: Acetaminophen not found in rxnorm_conso")
    
    print(f"✓ Found acetaminophen: RXCUI {acetaminophen_result[0]} - {acetaminophen_result[1]}")
    
    cur.execute("SELECT COUNT(*) FROM ontology.rxnorm_ndc")
    ndc_count = cur.fetchone()[0]
    
    if ndc_count == 0:
        raise RuntimeError("SMOKE TEST FAILED: No NDCs found in rxnorm_ndc")
    
    print(f"✓ Found {ndc_count:,} NDC mappings")
    
    tables = [
        "ontology.rxnorm_conso",
        "ontology.rxnorm_rel", 
        "ontology.rxnorm_sat",
        "ontology.rxnorm_ndc"
    ]
    
    print("\nTable counts:")
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count:,} rows")

def main():
    parser = argparse.ArgumentParser(description="Ingest RxNorm data into PostgreSQL")
    parser.add_argument("--zip", help="Path to local RxNorm ZIP file")
    parser.add_argument("--zip-url", help="URL to download RxNorm ZIP file")
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
            temp_dir = tempfile.mkdtemp(prefix="rxnorm_download_")
            zip_path = download_zip(args.zip_url, temp_dir)
        else:
            zip_path = args.zip
            if not os.path.exists(zip_path):
                raise FileNotFoundError(f"ZIP file not found: {zip_path}")
        
        extract_dir, zip_md5 = unzip_file(zip_path)
        print(f"ZIP MD5: {zip_md5}")
        
        rrf_files = {
            'conso': find_rrf_path(extract_dir, "RXNCONSO.RRF"),
            'rel': find_rrf_path(extract_dir, "RXNREL.RRF"),
            'sat': find_rrf_path(extract_dir, "RXNSAT.RRF")
        }
        
        print(f"Found RRF files:")
        for name, path in rrf_files.items():
            print(f"  {name}: {path}")
        
        database_url = get_database_url()
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        
        try:
            with conn.cursor() as cur:
                print("Creating schema and tables...")
                cur.execute(DDL_SQL)
                
                load_rxnorm_conso(cur, rrf_files['conso'], args.dry_run)
                load_rxnorm_rel(cur, rrf_files['rel'], args.dry_run)
                load_rxnorm_sat(cur, rrf_files['sat'], args.dry_run)
                build_ndc_map(cur, args.dry_run)
                
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
