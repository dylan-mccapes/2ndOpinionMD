#!/usr/bin/env python3
"""
Orphanet Data Ingestion Script

Loads Orphanet data from ZIP file or directory into PostgreSQL ontology schema.
Supports auto-detection of XML files and idempotent upserts.
"""

import argparse
import os
import sys
import zipfile
import tempfile
import io
import re
import xml.etree.ElementTree as ET
import psycopg2
import time
import hashlib
from psycopg2.extras import execute_values
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

def get_db_url():
    """Get database URL from environment variables."""
    url = os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd"
    return url.replace("+asyncpg", "")

def find_xmls(root_dir):
    """Auto-detect the three key Orphadata XMLs by root element."""
    paths = {}
    for dirpath, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith(".xml"):
                p = os.path.join(dirpath, f)
                try:
                    with open(p, "rb") as fh:
                        head = fh.read(2048)
                    
                    t = ET.parse(p)
                    root = t.getroot().tag.lower()
                    if "disorderlist" in root:
                        paths["product1"] = p
                    elif "genedisorderassociationlist" in root:
                        paths["product6"] = p
                    elif "hpodisordersetstatuslist" in root:
                        paths["product4"] = p
                except Exception:
                    pass
    return paths

def unzip_to_temp(zip_path):
    """Extract ZIP file to temporary directory."""
    tmp = tempfile.mkdtemp(prefix="orphadata_")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmp)
    return tmp

def parse_product1(p):
    """Parse product1 XML (disease list) for diseases, synonyms, and external refs."""
    diseases, synonyms, xrefs = [], [], []
    
    for event, elem in ET.iterparse(p, events=("end",)):
        if elem.tag.endswith("Disorder"):
            oc_elem = elem.find(".//{*}OrphaCode")
            name_elem = elem.find(".//{*}Name")
            dtyp_elem = elem.find(".//{*}DisorderType/{*}Name")
            defn_elem = elem.find(".//{*}Definition")
            
            if oc_elem is not None and name_elem is not None:
                oc = int(oc_elem.text)
                name = name_elem.text
                dtyp = dtyp_elem.text if dtyp_elem is not None else None
                defn = defn_elem.text if defn_elem is not None else None
                
                diseases.append((oc, name, dtyp, defn, None, None))
                
                for s in elem.findall(".//{*}SynonymList/{*}Synonym"):
                    syn_elem = s.find(".//{*}Synonym")
                    if syn_elem is not None:
                        lang = s.get("{http://www.w3.org/XML/1998/namespace}lang")
                        synonyms.append((oc, syn_elem.text, lang))
                
                for xr in elem.findall(".//{*}ExternalReferenceList/{*}ExternalReference"):
                    src_elem = xr.find(".//{*}Source")
                    ref_elem = xr.find(".//{*}Reference")
                    if src_elem is not None and ref_elem is not None:
                        xrefs.append((oc, src_elem.text, ref_elem.text))
            
            elem.clear()
    
    return diseases, synonyms, xrefs

def parse_product6(p):
    """Parse product6 XML (gene-disease associations)."""
    links = []
    
    for event, elem in ET.iterparse(p, events=("end",)):
        if elem.tag.endswith("GeneDisorderAssociation"):
            oc_elem = elem.find(".//{*}Disorder/{*}OrphaCode")
            gs_elem = elem.find(".//{*}Gene/{*}Symbol")
            
            entrez_elem = None
            ensg_elem = None
            for xr in elem.findall(".//{*}ExternalReferenceList/{*}ExternalReference"):
                src_elem = xr.find(".//{*}Source")
                ref_elem = xr.find(".//{*}Reference")
                if src_elem is not None and ref_elem is not None:
                    if src_elem.text == "EntrezGene":
                        entrez_elem = ref_elem
                    elif src_elem.text == "Ensembl":
                        ensg_elem = ref_elem
            
            assoc_elem = elem.find(".//{*}GeneDisorderAssociationType/{*}Name")
            inherit_elem = elem.find(".//{*}DisorderAssociationType/{*}Name")
            ev_elem = elem.find(".//{*}SourceOfValidation")
            
            if oc_elem is not None:
                oc = int(oc_elem.text)
                gs = gs_elem.text if gs_elem is not None else None
                entrez = entrez_elem.text if entrez_elem is not None else None
                ensg = ensg_elem.text if ensg_elem is not None else None
                assoc = assoc_elem.text if assoc_elem is not None else None
                inherit = inherit_elem.text if inherit_elem is not None else None
                ev = ev_elem.text if ev_elem is not None else None
                
                links.append((oc, gs, entrez, ensg, assoc, inherit, ev))
            
            elem.clear()
    
    return links

def parse_product4(p):
    """Parse product4 XML (phenotype-disease associations)."""
    phenos = []
    
    for event, elem in ET.iterparse(p, events=("end",)):
        if elem.tag.endswith("HPODisorderAssociation"):
            oc_elem = elem.find(".//{*}Disorder/{*}OrphaCode")
            hpo_id_elem = elem.find(".//{*}HPO/{*}HPOId")
            hpo_label_elem = elem.find(".//{*}HPO/{*}HPOTerm")
            freq_elem = elem.find(".//{*}HPOFrequency/{*}Name")
            diag_elem = elem.find(".//{*}DiagnosticCriteria")
            neg_elem = elem.find(".//{*}HPOOccurrence")
            
            if oc_elem is not None and hpo_id_elem is not None:
                oc = int(oc_elem.text)
                hpo_id = hpo_id_elem.text
                hpo_label = hpo_label_elem.text if hpo_label_elem is not None else None
                freq = freq_elem.text if freq_elem is not None else None
                diagnostic = (diag_elem.text.lower() == "true") if diag_elem is not None else False
                negated = (neg_elem.text.lower() == "excluded") if neg_elem is not None else False
                
                phenos.append((oc, hpo_id, hpo_label, freq, diagnostic, negated))
            
            elem.clear()
    
    return phenos

def copy(cur, table, cols, rows):
    """Insert rows using execute_values with ON CONFLICT DO NOTHING."""
    if not rows:
        return 0
    
    execute_values(cur,
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s "
        f"ON CONFLICT DO NOTHING", rows, page_size=5000)
    return len(rows)

def upsert_core(cur, diseases, synonyms, xrefs, genes, phenos):
    """Upsert all data with proper conflict handling."""
    execute_values(cur, """
        INSERT INTO ontology.orphanet_diseases
            (orpha_code, name, disorder_type, definition, prevalence_note, inheritance_note)
        VALUES %s
        ON CONFLICT (orpha_code) DO UPDATE SET
            name=EXCLUDED.name,
            disorder_type=EXCLUDED.disorder_type,
            definition=EXCLUDED.definition,
            ingested_at=now()
    """, diseases, page_size=5000)

    copy(cur, "ontology.orphanet_synonyms",
         ["orpha_code","synonym","lang"], synonyms)
    copy(cur, "ontology.orphanet_external_refs",
         ["orpha_code","source","ref"], xrefs)
    copy(cur, "ontology.orphanet_gene_links",
         ["orpha_code","gene_symbol","entrez_id","ensembl_id","association","inheritance","evidence"], genes)
    copy(cur, "ontology.orphanet_phenotype_links",
         ["orpha_code","hpo_id","hpo_label","frequency","diagnostic","negated"], phenos)

def main():
    """Main entry point."""
    ap = argparse.ArgumentParser(description="Ingest Orphanet data into PostgreSQL")
    ap.add_argument("--zip", help="Path to Orphadata ZIP file")
    ap.add_argument("--dir", help="Directory with Orphadata XMLs")
    ap.add_argument("--dry-run", action="store_true", help="Parse files but don't write to database")
    args = ap.parse_args()

    if not args.zip and not args.dir:
        ap.error("Provide --zip or --dir")

    workdir = args.dir
    if args.zip:
        print(f"Extracting {args.zip}...")
        workdir = unzip_to_temp(args.zip)

    print(f"Scanning {workdir} for XML files...")
    xmls = find_xmls(workdir)
    
    required = {"product1", "product6", "product4"}
    found = set(xmls.keys())
    if not required <= found:
        missing = required - found
        print(f"Could not auto-detect required XMLs: {missing}")
        print(f"Found: {found}")
        sys.exit(2)

    print("Parsing XML files...")
    t0 = time.time()
    
    diseases, synonyms, xrefs = parse_product1(xmls["product1"])
    genes = parse_product6(xmls["product6"])
    phenos = parse_product4(xmls["product4"])
    
    parse_time = time.time() - t0
    print(f"Parsed: diseases={len(diseases)} synonyms={len(synonyms)} "
          f"xrefs={len(xrefs)} genes={len(genes)} phenos={len(phenos)} "
          f"in {parse_time:.1f}s")

    if args.dry_run:
        print("DRY RUN: no database writes.")
        return

    ddl_path = os.path.join(os.path.dirname(__file__), "ddl_orphanet.sql")
    with open(ddl_path) as f:
        ddl = f.read()

    print("Connecting to database...")
    db = psycopg2.connect(get_db_url())
    db.autocommit = False
    
    try:
        with db.cursor() as cur:
            print("Creating schema and tables...")
            cur.execute(ddl)
            
            print("Upserting data...")
            upsert_core(cur, diseases, synonyms, xrefs, genes, phenos)
            
        db.commit()
        print("✅ Successfully committed all data.")
        
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ontology.orphanet_diseases")
            disease_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ontology.orphanet_gene_links")
            gene_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ontology.orphanet_phenotype_links")
            pheno_count = cur.fetchone()[0]
            
        print(f"Final counts: diseases={disease_count:,} genes={gene_count:,} phenotypes={pheno_count:,}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
