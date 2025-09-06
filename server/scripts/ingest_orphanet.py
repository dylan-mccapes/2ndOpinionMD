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

def find_xmls(root_dir: str) -> dict[str, str]:
    """
    Auto-detect Orphadata XMLs. We sniff file *names* and *contents*,
    and fall back to parsing the root tag if needed.
    Returns dict with keys: product1, product6, product4
    """
    import xml.etree.ElementTree as ET
    hits: dict[str, str] = {}
    want = {"product1", "product6", "product4"}

    def which_product(fname: str, head: str) -> str | None:
        lfn = fname.lower()
        lhead = head.lower()
        if "product1" in lfn or ("disorder" in lfn and "list" in lfn):
            return "product1"
        if "product6" in lfn or "genedisorder" in lfn or "gene" in lfn:
            return "product6"
        if "product4" in lfn or "hpo" in lfn:
            return "product4"
        if "disorderlist" in lhead:
            return "product1"
        if "genedisorderassociation" in lhead:
            return "product6"
        if "hpodisordersetstatus" in lhead or "hpodisorderassociation" in lhead:
            return "product4"
        return None

    for dirpath, _, files in os.walk(root_dir):
        for fname in files:
            if not fname.lower().endswith(".xml"):
                continue
            p = os.path.join(dirpath, fname)
            try:
                with open(p, "rb") as fh:
                    head = fh.read(131072).decode("utf-8", errors="ignore")  # 128KB sniff
                k = which_product(fname, head)
                if not k:
                    try:
                        root = ET.parse(p).getroot()
                        tag = root.tag.lower()
                        if "disorderlist" in tag:
                            k = "product1"
                        elif "genedisorderassociationlist" in tag:
                            k = "product6"
                        elif "hpodisordersetstatus" in tag or "hpodisorderassociation" in tag:
                            k = "product4"
                    except Exception:
                        k = None
                if k and k not in hits:
                    hits[k] = p
                    if hits.keys() >= want:
                        return hits
            except Exception:
                continue
    return hits

def unzip_to_temp(zip_path):
    """Extract ZIP to temporary directory."""
    tmp = tempfile.mkdtemp(prefix="orphadata_")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmp)
    return tmp

def parse_product1(p):
    """Parse disease list XML (product1): diseases, synonyms, external refs."""
    diseases, synonyms, xrefs = [], [], []

    for event, elem in ET.iterparse(p, events=("end",)):
        if elem.tag.endswith("Disorder"):
            oc_text = elem.findtext(".//{*}OrphaCode")
            if not oc_text:
                elem.clear(); continue

            oc_num = int(oc_text)
            oc_code = f"ORPHA:{oc_num}"

            name = (elem.findtext(".//{*}Name") or "").strip()
            dtyp = elem.findtext(".//{*}DisorderType/{*}Name")
            defn = elem.findtext(".//{*}Definition")
            status = elem.findtext(".//{*}DisorderStatus/{*}Name")
            expert_link = elem.findtext(".//{*}ExpertLink")

            diseases.append((oc_code, oc_num, name, dtyp, defn, status, expert_link))

            # Synonyms
            for s in elem.findall(".//{*}SynonymList/{*}Synonym"):
                term = s.findtext(".//{*}Synonym") or (s.text or "")
                term = term.strip()
                if not term:
                    continue
                # xml:lang could be attribute 'lang' or xml:lang namespace
                lang = (
                    s.get('{http://www.w3.org/XML/1998/namespace}lang')
                    or s.get('lang') or ''
                ).strip()
                scope = (s.findtext(".//{*}SynonymType/{*}Name") or '').strip()
                synonyms.append((oc_code, term, lang, scope))

            # External refs
            for xr in elem.findall(".//{*}ExternalReferenceList/{*}ExternalReference"):
                src = (xr.findtext(".//{*}Source") or "").strip()
                ref = (xr.findtext(".//{*}Reference") or "").strip()
                url = xr.findtext(".//{*}URL")
                if src and ref:
                    xrefs.append((oc_code, src, ref, url))

            elem.clear()

    return diseases, synonyms, xrefs


def parse_product6(p: str):
    """Parse product6 (Gene–Disease associations) with robust tag handling."""
    links = []
    for _, elem in ET.iterparse(p, events=("end",)):
        if not elem.tag.endswith("GeneDisorderAssociation"):
            continue

        oc_txt = elem.findtext(".//{*}Disorder/{*}OrphaCode")
        if not oc_txt:
            elem.clear(); continue
        orpha_code = f"ORPHA:{int(oc_txt)}"

        gene_symbol = (
            elem.findtext(".//{*}Gene/{*}Symbol")
            or elem.findtext(".//{*}Gene/{*}Name")
            or ""
        ).strip().upper()
        if not gene_symbol:
            elem.clear(); continue

        entrez = None
        ensembl = None

        for ref in elem.findall(".//{*}Gene/{*}ExternalReferenceList/{*}ExternalReference"):
            src = (ref.findtext(".//{*}Source") or "").strip()
            rid = (ref.findtext(".//{*}Reference") or "").strip()
            if src == "EntrezGene" and rid: entrez = rid
            if src == "Ensembl"   and rid: ensembl = rid

        if not (entrez or ensembl):
            for ref in elem.findall(".//{*}ExternalReferenceList/{*}ExternalReference"):
                src = (ref.findtext(".//{*}Source") or "").strip()
                rid = (ref.findtext(".//{*}Reference") or "").strip()
                if src == "EntrezGene" and rid: entrez = rid
                if src == "Ensembl"   and rid: ensembl = rid

        assoc_type = (
            elem.findtext(".//{*}GeneDisorderAssociationType/{*}Name")
            or elem.findtext(".//{*}GeneDisorderAssociationType")
            or ""
        ).strip()

        inheritance = (
            elem.findtext(".//{*}DisorderGeneAssociationType/{*}Name")
            or elem.findtext(".//{*}DisorderAssociationType/{*}Name")
            or elem.findtext(".//{*}DisorderGeneAssociationType")
            or elem.findtext(".//{*}DisorderAssociationType")
            or ""
        ).strip()

        evidence = (
            elem.findtext(".//{*}SourceOfValidation")
            or ""
        ).strip()

        links.append((orpha_code, gene_symbol, entrez, ensembl, assoc_type, inheritance, evidence))
        elem.clear()
    return links

def parse_product4(p: str):
    """Parse product4 (HPO–Disease associations) with tag/frequency normalization."""
    phenos = []
    for _, elem in ET.iterparse(p, events=("end",)):
        if not elem.tag.endswith("HPODisorderAssociation"):
            continue

        oc_txt = elem.findtext(".//{*}Disorder/{*}OrphaCode")
        hpo_id = (
            elem.findtext(".//{*}HPO/{*}HPOId")
            or elem.findtext(".//{*}HPO/{*}Id")
            or elem.findtext(".//{*}HPO/{*}id")
        )
        if not oc_txt or not hpo_id:
            elem.clear(); continue

        orpha_code = f"ORPHA:{int(oc_txt)}"
        hpo_label = (
            elem.findtext(".//{*}HPO/{*}HPOTerm")
            or elem.findtext(".//{*}HPO/{*}Name")
        )

        freq_raw = (
            elem.findtext(".//{*}HPOFrequency/{*}Name")
            or elem.findtext(".//{*}HPOFrequency")
        )
        frequency = normalize_frequency(freq_raw)

        diag_text = elem.findtext(".//{*}DiagnosticCriteria")
        diagnostic = (str(diag_text).lower() == "true") if diag_text else False

        occ_text = elem.findtext(".//{*}HPOOccurrence")
        negated = (str(occ_text).lower() == "excluded") if occ_text else False

        phenos.append((orpha_code, hpo_id, hpo_label, frequency, diagnostic, negated))
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

def dedup_diseases(rows):
    """Deduplicate by orpha_code, preferring non-empty fields."""
    best = {}
    for oc, onum, name, dtyp, defn, status, link in rows:
        cur = best.get(oc)
        if not cur:
            best[oc] = [onum, name, dtyp, defn, status, link]
            continue
        cur[0] = cur[0] or onum
        cur[1] = cur[1] or name
        cur[2] = cur[2] or dtyp
        cur[3] = cur[3] or defn
        cur[4] = cur[4] or status
        cur[5] = cur[5] or link
    return [(oc, v[0], v[1], v[2], v[3], v[4], v[5]) for oc, v in best.items()]

def upsert_core(cur, diseases, synonyms, xrefs, genes, phenos):
    # diseases
    if diseases:
        diseases = dedup_diseases(diseases)
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

    # synonyms
    if synonyms:
        syn_rows = [(oc, term, (lang or ''), (scope or '')) for (oc, term, lang, scope) in synonyms]
        execute_values(cur,
            "INSERT INTO ontology.orphanet_synonyms (orpha_code, synonym, lang, scope) VALUES %s ON CONFLICT DO NOTHING",
            syn_rows, page_size=5000)

    # external refs
    if xrefs:
        execute_values(cur,
            "INSERT INTO ontology.orphanet_external_refs (orpha_code, source, ref, url) VALUES %s ON CONFLICT DO NOTHING",
            xrefs, page_size=5000)

    # genes
    if genes:
        gene_rows = [(oc, sym, entrez, ensembl, (assoc or ''), inheritance, evidence)
                     for (oc, sym, entrez, ensembl, assoc, inheritance, evidence) in genes]
        execute_values(cur, """
            INSERT INTO ontology.orphanet_gene_links
                (orpha_code, gene_symbol, entrez_id, ensembl_id, association_type, inheritance, evidence)
            VALUES %s ON CONFLICT DO NOTHING
        """, gene_rows, page_size=5000)

    # phenotypes
    if phenos:
        execute_values(cur, """
            INSERT INTO ontology.orphanet_phenotype_links
                (orpha_code, hpo_id, hpo_label, frequency, diagnostic, negated)
            VALUES %s ON CONFLICT DO NOTHING
        """, phenos, page_size=5000)

def main():
    """Main entry point for Orphanet ingestion."""
    ap = argparse.ArgumentParser(description="Import Orphanet (Orphadata) XMLs into PostgreSQL")
    ap.add_argument("--zip", help="Path to Orphadata ZIP file (containing en_product1/4/6.xml)")
    ap.add_argument("--dir", help="Directory containing Orphadata XMLs (en_product1/4/6.xml)")
    ap.add_argument("--p1", help="Path to product1 XML (diseases)")
    ap.add_argument("--p4", help="Path to product4 XML (HPO links)")
    ap.add_argument("--p6", help="Path to product6 XML (gene links)")
    ap.add_argument("--dry-run", action="store_true", help="Parse only, do not write to database")
    args = ap.parse_args()

    if not args.zip and not args.dir and not (args.p1 and args.p4 and args.p6):
        ap.error("Provide --zip or --dir, or specify all three XMLs with --p1/--p4/--p6")

    # 1) Resolve working directory
    if args.zip:
        print(f"Extracting {args.zip}...")
        workdir = unzip_to_temp(args.zip)
    elif args.dir:
        workdir = args.dir
    else:
        workdir = ""

    # 2) Merge overrides + autodetect XMLs
    xmls = {}
    if args.p1: xmls["product1"] = args.p1
    if args.p4: xmls["product4"] = args.p4
    if args.p6: xmls["product6"] = args.p6

    if set(xmls.keys()) != {"product1", "product4", "product6"}:
        print(f"Scanning {workdir} for XML files...")
        auto = find_xmls(workdir)
        for k, v in auto.items():
            xmls.setdefault(k, v)

    required = {"product1", "product6", "product4"}
    found = set(xmls.keys())
    if not required <= found:
        missing = required - found
        print(f"❌ Could not auto-detect required XMLs: {missing}")
        print(f"Found: {found}")
        print("Tip: pass explicit paths with --p1/--p4/--p6")
        sys.exit(2)

    print(f"✅ Found XMLs: {set(xmls.keys())}")
    for k in ("product1","product6","product4"):
        print(f"  {k}: {os.path.basename(xmls[k])}")

    # 3) Parse XMLs
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

    # 4) Read DDL
    ddl_path = os.path.join(os.path.dirname(__file__), "ddl_orphanet.sql")
    with open(ddl_path, "r", encoding="utf-8") as f:
        ddl_sql = f.read()

    # 5) DB work (DDL -> UPSERTS) with clean cursor scoping & commits
    print("Connecting to database...")
    db = psycopg2.connect(get_db_url())

    try:
        # Phase A: Ensure schema/tables/indexes
        with db.cursor() as cur:
            print("Creating schema...")
            cur.execute(ddl_sql)
        db.commit()

        # Phase B: Upserts
        with db.cursor() as cur:
            print("Upserting data...")
            upsert_core(cur, diseases, synonyms, xrefs, genes, phenos)
        db.commit()

        print("✅ Successfully committed all data.")

        # Phase C: Stats
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
        print(f"❌ Database error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
