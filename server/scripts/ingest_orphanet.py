#!/usr/bin/env python3
import argparse, os, sys, zipfile, tempfile, io, re
import xml.etree.ElementTree as ET
import psycopg2, time, hashlib
from psycopg2.extras import execute_values

DDL = open(os.path.join(os.path.dirname(__file__), "ddl_orphanet.sql")).read()

def get_db_url():
    url = os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd"
    return url.replace("+asyncpg", "")

def normalize_frequency(freq_text):
    """Normalize Orphanet frequency to canonical strings."""
    if not freq_text:
        return None
    
    freq_lower = freq_text.lower().strip()
    
    freq_map = {
        'obligate': 'Obligate (100%)',
        '100%': 'Obligate (100%)',
        'very frequent': 'Very frequent (80–99%)',
        'frequent': 'Frequent (30–79%)',
        'occasional': 'Occasional (5–29%)',
        'very rare': 'Very rare (<5%)',
        'excluded': 'Excluded (0%)',
        'rare': 'Very rare (<5%)',
    }
    
    if '%' in freq_text:
        if '100' in freq_text:
            return 'Obligate (100%)'
        elif any(x in freq_text for x in ['80', '90', '99']):
            return 'Very frequent (80–99%)'
        elif any(x in freq_text for x in ['30', '40', '50', '60', '70']):
            return 'Frequent (30–79%)'
        elif any(x in freq_text for x in ['5', '10', '20', '29']):
            return 'Occasional (5–29%)'
        elif any(x in freq_text for x in ['0', '<5']):
            return 'Very rare (<5%)'
    
    for key, value in freq_map.items():
        if key in freq_lower:
            return value
    
    return freq_text

def find_xmls(root_dir):
    """Auto-detect relevant XMLs inside the ZIP/dir."""
    paths = {}
    for dirpath, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith(".xml"):
                p = os.path.join(dirpath, f)
                try:
                    with open(p, "rb") as fh:
                        head = fh.read(4096).decode('utf-8', errors='ignore')
                    
                    head_lower = head.lower()
                    if "disorderlist" in head_lower:
                        paths["product1"] = p
                    elif "genedisorderassociationlist" in head_lower:
                        paths["product6"] = p  
                    elif "hpodisordersetstatuslist" in head_lower:
                        paths["product4"] = p
                except Exception:
                    pass
    return paths

def unzip_to_temp(zip_path):
    """Extract ZIP to temporary directory."""
    tmp = tempfile.mkdtemp(prefix="orphadata_")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmp)
    return tmp

def parse_product1(p):
    """Parse disease list XML (product1)."""
    diseases, synonyms, xrefs = [], [], []
    
    for event, elem in ET.iterparse(p, events=("end",)):
        if elem.tag.endswith("Disorder"):
            oc_elem = elem.find(".//{*}OrphaCode")
            if oc_elem is None:
                elem.clear()
                continue
                
            oc_num = int(oc_elem.text)
            oc_code = f"ORPHA:{oc_num}"
            
            name = elem.findtext(".//{*}Name") or ""
            dtyp = elem.findtext(".//{*}DisorderType/{*}Name")
            defn = elem.findtext(".//{*}Definition")
            status = elem.findtext(".//{*}DisorderStatus/{*}Name")
            expert_link = elem.findtext(".//{*}ExpertLink")
            
            diseases.append((oc_code, oc_num, name, dtyp, defn, status, expert_link))
            
            for s in elem.findall(".//{*}SynonymList/{*}Synonym"):
                syn_text = s.findtext(".//{*}Synonym")
                lang = s.get("{http://www.w3.org/XML/1998/namespace}lang")
                scope = s.findtext(".//{*}SynonymType/{*}Name")
                if syn_text:
                    synonyms.append((oc_code, syn_text, lang, scope))
            
            for xr in elem.findall(".//{*}ExternalReferenceList/{*}ExternalReference"):
                src = xr.findtext(".//{*}Source")
                ref = xr.findtext(".//{*}Reference")
                url = xr.findtext(".//{*}URL")
                if src and ref:
                    xrefs.append((oc_code, src, ref, url))
            
            elem.clear()
    
    return diseases, synonyms, xrefs

def parse_product6(p):
    """Parse gene-disease associations XML (product6)."""
    links = []
    
    for event, elem in ET.iterparse(p, events=("end",)):
        if elem.tag.endswith("GeneDisorderAssociation"):
            oc_elem = elem.find(".//{*}Disorder/{*}OrphaCode")
            if oc_elem is None:
                elem.clear()
                continue
                
            oc_code = f"ORPHA:{oc_elem.text}"
            
            gs = elem.findtext(".//{*}Gene/{*}Symbol")
            if not gs:
                elem.clear()
                continue
                
            gs = gs.upper()  # Normalize gene symbols to uppercase
            
            entrez = None
            ensembl = None
            for ref in elem.findall(".//{*}Gene/{*}ExternalReferenceList/{*}ExternalReference"):
                src = ref.findtext(".//{*}Source")
                ref_id = ref.findtext(".//{*}Reference")
                if src == "EntrezGene":
                    entrez = ref_id
                elif src == "Ensembl":
                    ensembl = ref_id
            
            assoc_type = elem.findtext(".//{*}GeneDisorderAssociationType/{*}Name")
            inheritance = elem.findtext(".//{*}DisorderGeneAssociationType/{*}Name")
            evidence = elem.findtext(".//{*}SourceOfValidation")
            
            links.append((oc_code, gs, entrez, ensembl, assoc_type, inheritance, evidence))
            elem.clear()
    
    return links

def parse_product4(p):
    """Parse HPO-disease associations XML (product4)."""
    phenos = []
    
    for event, elem in ET.iterparse(p, events=("end",)):
        if elem.tag.endswith("HPODisorderAssociation"):
            oc_elem = elem.find(".//{*}Disorder/{*}OrphaCode")
            if oc_elem is None:
                elem.clear()
                continue
                
            oc_code = f"ORPHA:{oc_elem.text}"
            
            hpo_id = elem.findtext(".//{*}HPO/{*}HPOId")
            hpo_label = elem.findtext(".//{*}HPO/{*}HPOTerm")
            
            if not hpo_id:
                elem.clear()
                continue
            
            freq_raw = elem.findtext(".//{*}HPOFrequency/{*}Name")
            freq = normalize_frequency(freq_raw)
            
            diag_text = elem.findtext(".//{*}DiagnosticCriteria")
            diagnostic = str(diag_text).lower() == "true" if diag_text else False
            
            occur_text = elem.findtext(".//{*}HPOOccurrence")
            negated = str(occur_text).lower() == "excluded" if occur_text else False
            
            phenos.append((oc_code, hpo_id, hpo_label, freq, diagnostic, negated))
            elem.clear()
    
    return phenos

def copy_with_dedup(cur, table, cols, rows):
    """Copy rows with deduplication using staging table."""
    if not rows:
        return 0
    
    staging_table = f"{table}_staging"
    col_defs = ", ".join([f"{col} TEXT" for col in cols])
    cur.execute(f"CREATE TEMP TABLE {staging_table} ({col_defs})")
    
    execute_values(cur, 
        f"INSERT INTO {staging_table} ({', '.join(cols)}) VALUES %s",
        rows, page_size=5000)
    
    cur.execute(f"""
        INSERT INTO {table} ({', '.join(cols)})
        SELECT DISTINCT * FROM {staging_table}
        ON CONFLICT DO NOTHING
    """)
    
    return len(rows)

def upsert_core(cur, diseases, synonyms, xrefs, genes, phenos):
    """Upsert all data with proper ordering and conflict handling."""
    
    if diseases:
        execute_values(cur, """
            INSERT INTO ontology.orphanet_diseases
                (orpha_code, orpha_num, name, disorder_type, definition, status, expert_link)
            VALUES %s
            ON CONFLICT (orpha_code) DO UPDATE SET
                name=EXCLUDED.name,
                disorder_type=EXCLUDED.disorder_type,
                definition=EXCLUDED.definition,
                status=EXCLUDED.status,
                expert_link=EXCLUDED.expert_link,
                updated_at=NOW()
        """, diseases, page_size=5000)
    
    copy_with_dedup(cur, "ontology.orphanet_synonyms",
                   ["orpha_code","synonym","lang","scope"], synonyms)
    copy_with_dedup(cur, "ontology.orphanet_external_refs", 
                   ["orpha_code","source","ref","url"], xrefs)
    copy_with_dedup(cur, "ontology.orphanet_gene_links",
                   ["orpha_code","gene_symbol","entrez_id","ensembl_id","association_type","inheritance","evidence"], genes)
    copy_with_dedup(cur, "ontology.orphanet_phenotype_links",
                   ["orpha_code","hpo_id","hpo_label","frequency","diagnostic","negated"], phenos)

def main():
    ap = argparse.ArgumentParser(description="Import Orphanet data into PostgreSQL")
    ap.add_argument("--zip", help="Path to Orphadata ZIP file")
    ap.add_argument("--dir", help="Directory with Orphadata XMLs")
    ap.add_argument("--dry-run", action="store_true", help="Parse only, don't write to DB")
    ap.add_argument("--schema", default="ontology", help="Database schema (default: ontology)")
    args = ap.parse_args()

    if not args.zip and not args.dir:
        ap.error("Provide --zip or --dir")

    workdir = args.dir
    if args.zip:
        print(f"Extracting {args.zip}...")
        workdir = unzip_to_temp(args.zip)

    xmls = find_xmls(workdir)
    required = {"product1", "product6", "product4"}
    found = set(xmls.keys())
    
    if not required <= found:
        missing = required - found
        print(f"❌ Could not auto-detect required XMLs: {missing}")
        print(f"Found: {found}")
        sys.exit(2)

    print(f"✅ Found XMLs: {found}")
    for key, path in xmls.items():
        print(f"  {key}: {os.path.basename(path)}")

    print("Parsing XMLs...")
    t0 = time.time()
    
    diseases, synonyms, xrefs = parse_product1(xmls["product1"])
    genes = parse_product6(xmls["product6"])
    phenos = parse_product4(xmls["product4"])
    
    parse_time = time.time() - t0
    print(f"✅ Parsed in {parse_time:.1f}s:")
    print(f"  diseases: {len(diseases):,}")
    print(f"  synonyms: {len(synonyms):,}")
    print(f"  external_refs: {len(xrefs):,}")
    print(f"  gene_links: {len(genes):,}")
    print(f"  phenotype_links: {len(phenos):,}")

    if args.dry_run:
        print("🔍 DRY RUN: No database writes performed.")
        return

    print("Connecting to database...")
    db = psycopg2.connect(get_db_url())
    db.autocommit = False
    
    try:
        with db.cursor() as cur:
            print("Creating schema...")
            cur.execute(DDL)
            
            print("Upserting data...")
            upsert_core(cur, diseases, synonyms, xrefs, genes, phenos)
            
        db.commit()
        print("✅ Successfully committed all data.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Database error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
