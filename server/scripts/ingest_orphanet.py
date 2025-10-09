#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, os, sys, zipfile, tempfile, time
from pathlib import Path
import xml.etree.ElementTree as ET

import psycopg2
from psycopg2.extras import execute_values


# ---------------------------------------------------------------------
# Paths & defaults
# ---------------------------------------------------------------------
THIS_DIR  = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
DEFAULT_DDL = REPO_ROOT / "database" / "sql" / "ddl_orphanet.sql"


# ---------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------
def get_db_url() -> str:
    """
    Prefer SYNC_DATABASE_URL (your reporting scripts use this),
    then DATABASE_URL, then a sane local default.
    """
    url = (
        os.getenv("SYNC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"
    )
    return url.replace("+asyncpg", "")


# ---------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------
def normalize_frequency(freq_text: str | None) -> str | None:
    """Normalize Orphanet frequency to canonical strings."""
    if not freq_text:
        return None
    s = str(freq_text).strip()
    sl = s.lower()

    # quick canonical map
    fmap = {
        "obligate": "Obligate (100%)",
        "100%": "Obligate (100%)",
        "very frequent": "Very frequent (80–99%)",
        "frequent": "Frequent (30–79%)",
        "occasional": "Occasional (5–29%)",
        "very rare": "Very rare (<5%)",
        "excluded": "Excluded (0%)",
        "rare": "Very rare (<5%)",
    }
    for k, v in fmap.items():
        if k in sl:
            return v

    # numeric hints
    if "%" in s:
        if "100" in s:
            return "Obligate (100%)"
        for x in ("80", "90", "99"):
            if x in s:
                return "Very frequent (80–99%)"
        for x in ("30", "40", "50", "60", "70"):
            if x in s:
                return "Frequent (30–79%)"
        for x in ("5", "10", "20", "29"):
            if x in s:
                return "Occasional (5–29%)"
        if "0" in s or "<5" in s:
            return "Very rare (<5%)"

    return s


def unzip_to_temp(zip_path: str) -> str:
    tmp = tempfile.mkdtemp(prefix="orphadata_")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmp)
    return tmp


def find_xmls(root_dir: str) -> dict[str, str]:
    """
    Auto-detect Orphadata XMLs in a directory.
    Returns dict with keys: product1, product6, product4
    """
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
                    head = fh.read(131072).decode("utf-8", errors="ignore")
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
                    if set(hits.keys()) >= want:
                        return hits
            except Exception:
                continue
    return hits


# ------------------ product1 (disease list) ------------------
def parse_product1(p: str):
    diseases: list[tuple] = []
    synonyms: list[tuple] = []
    xrefs: list[tuple] = []

    for _, elem in ET.iterparse(p, events=("end",)):
        if elem.tag.endswith("Disorder"):
            oc_text = elem.findtext(".//{*}OrphaCode")
            if not oc_text:
                elem.clear()
                continue
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


# ------------------ product6 (gene links) ------------------
def parse_product6(p: str):
    links: list[tuple] = []
    root = ET.parse(p).getroot()

    for disorder in root.findall('.//{*}Disorder'):
        oc_txt = disorder.findtext('./{*}OrphaCode') or disorder.findtext('./{*}OrphaNumber')
        if not (oc_txt and oc_txt.strip().isdigit()):
            continue
        orpha_code = f"ORPHA:{int(oc_txt)}"

        assocs = disorder.findall('.//{*}DisorderGeneAssociation') + \
                 disorder.findall('.//{*}GeneDisorderAssociation')

        for assoc in assocs:
            gene_symbol = (
                assoc.findtext('.//{*}Gene/{*}Symbol') or
                assoc.findtext('.//{*}Gene/{*}Name') or ''
            ).strip().upper()
            if not gene_symbol:
                continue

            entrez = None
            ensembl = None
            # Prefer gene-level refs
            for ref in assoc.findall('.//{*}Gene/{*}ExternalReferenceList/{*}ExternalReference'):
                src = (ref.findtext('.//{*}Source') or '').strip()
                rid = (ref.findtext('.//{*}Reference') or '').strip()
                if src == 'EntrezGene' and rid:
                    entrez = rid
                elif src == 'Ensembl' and rid:
                    ensembl = rid
            if not (entrez or ensembl):
                # association-level refs
                for ref in assoc.findall('.//{*}ExternalReferenceList/{*}ExternalReference'):
                    src = (ref.findtext('.//{*}Source') or '').strip()
                    rid = (ref.findtext('.//{*}Reference') or '').strip()
                    if src == 'EntrezGene' and rid:
                        entrez = rid
                    elif src == 'Ensembl' and rid:
                        ensembl = rid

            assoc_type = (
                assoc.findtext('.//{*}GeneDisorderAssociationType/{*}Name') or
                assoc.findtext('.//{*}GeneDisorderAssociationType') or ''
            ).strip()
            inheritance = (
                assoc.findtext('.//{*}DisorderGeneAssociationType/{*}Name') or
                assoc.findtext('.//{*}DisorderAssociationType/{*}Name') or
                assoc.findtext('.//{*}DisorderGeneAssociationType') or
                assoc.findtext('.//{*}DisorderAssociationType') or ''
            ).strip()
            evidence = (assoc.findtext('.//{*}SourceOfValidation') or '').strip()

            links.append((orpha_code, gene_symbol, entrez, ensembl, assoc_type, inheritance, evidence))

    return links


# ------------------ product4 (phenotype/HPO links) ------------------
def parse_product4(p: str):
    phenos: list[tuple] = []
    root = ET.parse(p).getroot()

    for disorder in root.findall('.//{*}Disorder'):
        oc_txt = disorder.findtext('./{*}OrphaCode') or disorder.findtext('./{*}OrphaNumber')
        if not (oc_txt and oc_txt.strip().isdigit()):
            continue
        orpha_code = f"ORPHA:{int(oc_txt)}"

        assocs = disorder.findall('.//{*}HPODisorderAssociation') + \
                 disorder.findall('.//{*}HPODisorderSetStatus')

        for assoc in assocs:
            hpo_id = (
                assoc.findtext('.//{*}HPO/{*}HPOId') or
                assoc.findtext('.//{*}HPO/{*}Id') or
                assoc.findtext('.//{*}HPO/{*}id')
            )
            if not hpo_id:
                continue

            hpo_label = (
                assoc.findtext('.//{*}HPO/{*}HPOTerm') or
                assoc.findtext('.//{*}HPO/{*}Name')
            )

            freq_raw = (
                assoc.findtext('.//{*}HPOFrequency/{*}Name') or
                assoc.findtext('.//{*}HPOFrequency')
            )
            frequency = normalize_frequency(freq_raw)

            diag_text = assoc.findtext('.//{*}DiagnosticCriteria')
            diagnostic = (str(diag_text).lower() == 'true') if diag_text else False

            occ_text = assoc.findtext('.//{*}HPOOccurrence')
            negated = (str(occ_text).lower() == 'excluded') if occ_text else False

            phenos.append((orpha_code, hpo_id, hpo_label, frequency, diagnostic, negated))

    return phenos


# ---------------------------------------------------------------------
# Upsert logic
# ---------------------------------------------------------------------
def _dedup_diseases(rows: list[tuple]) -> list[tuple]:
    """Deduplicate by orpha_code, preferring non-empty fields."""
    best: dict[str, list] = {}
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
    return [(oc, *v) for oc, v in best.items()]


def upsert_core(cur, diseases, synonyms, xrefs, genes, phenos):
    # diseases
    if diseases:
        diseases = _dedup_diseases(diseases)
        execute_values(cur, """
            INSERT INTO ontology.orphanet_diseases
                (orpha_code, orpha_num, name, disorder_type, definition, status, expert_link)
            VALUES %s
            ON CONFLICT (orpha_code) DO UPDATE SET
                orpha_num     = EXCLUDED.orpha_num,
                name          = EXCLUDED.name,
                disorder_type = EXCLUDED.disorder_type,
                definition    = EXCLUDED.definition,
                status        = EXCLUDED.status,
                expert_link   = EXCLUDED.expert_link,
                updated_at    = NOW()
        """, diseases, page_size=5000)

    # synonyms
    if synonyms:
        syn_rows = [(oc, term, (lang or ''), (scope or '')) for (oc, term, lang, scope) in synonyms]
        execute_values(cur, """
            INSERT INTO ontology.orphanet_synonyms
                (orpha_code, synonym, lang, scope)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, syn_rows, page_size=5000)

    # external refs
    if xrefs:
        execute_values(cur, """
            INSERT INTO ontology.orphanet_external_refs
                (orpha_code, source, ref, url)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, xrefs, page_size=5000)

    # genes
    if genes:
        gene_rows = [(oc, sym, entrez, ensembl, (assoc or ''), inheritance, evidence)
                     for (oc, sym, entrez, ensembl, assoc, inheritance, evidence) in genes]
        execute_values(cur, """
            INSERT INTO ontology.orphanet_gene_links
                (orpha_code, gene_symbol, entrez_id, ensembl_id, association_type, inheritance, evidence)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, gene_rows, page_size=5000)

    # phenotypes
    if phenos:
        execute_values(cur, """
            INSERT INTO ontology.orphanet_phenotype_links
                (orpha_code, hpo_id, hpo_label, frequency, diagnostic, negated)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, phenos, page_size=5000)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Import Orphanet (Orphadata) XMLs into PostgreSQL")
    ap.add_argument("--zip", help="Path to Orphadata ZIP file (contains en_product1/4/6.xml)")
    ap.add_argument("--dir", help="Directory containing Orphadata XMLs (en_product1/4/6.xml)")
    ap.add_argument("--p1",  help="Path to product1 XML (diseases)")
    ap.add_argument("--p4",  help="Path to product4 XML (phenotype/HPO)")
    ap.add_argument("--p6",  help="Path to product6 XML (gene links)")
    ap.add_argument("--ddl", default=str(DEFAULT_DDL),
                    help=f"Path to DDL SQL (default: {DEFAULT_DDL})")
    ap.add_argument("--dry-run", action="store_true", help="Parse only; no DB writes")
    args = ap.parse_args()

    # Input validation
    if not args.zip and not args.dir and not (args.p1 and args.p4 and args.p6):
        ap.error("Provide --zip or --dir, or specify all three XMLs with --p1/--p4/--p6")

    # Working dir
    if args.zip:
        print(f"Extracting {args.zip} ...")
        workdir = unzip_to_temp(args.zip)
    elif args.dir:
        workdir = args.dir
    else:
        workdir = ""

    # Locate xmls (explicit overrides first, then autodetect in dir/zip)
    xmls: dict[str, str] = {}
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

    print("✅ Found XMLs:")
    print(f"  product1: {Path(xmls['product1']).name}")
    print(f"  product6: {Path(xmls['product6']).name}")
    print(f"  product4: {Path(xmls['product4']).name}")

    # Parse
    print("Parsing XMLs...")
    t0 = time.time()
    diseases, synonyms, xrefs = parse_product1(xmls["product1"])
    genes   = parse_product6(xmls["product6"])
    phenos  = parse_product4(xmls["product4"])
    parse_s = time.time() - t0

    # keep gene links only to known Orpha diseases (defensive)
    known_orphas = {d[0] for d in diseases}  # orpha_code
    if genes:
        genes = [g for g in genes if g[0] in known_orphas]

    print(f"✅ Parsed in {parse_s:.1f}s:")
    print(f"  diseases:        {len(diseases):,}")
    print(f"  synonyms:        {len(synonyms):,}")
    print(f"  external_refs:   {len(xrefs):,}")
    print(f"  gene_links:      {len(genes):,}")
    print(f"  phenotype_links: {len(phenos):,}")

    if args.dry_run:
        print("🔍 DRY RUN — no database writes.")
        return

    # Read DDL
    ddl_path = Path(args.ddl)
    if not ddl_path.exists():
        print(f"❌ DDL not found: {ddl_path}")
        sys.exit(1)
    ddl_sql = ddl_path.read_text(encoding="utf-8")

    # DB work
    dsn = get_db_url()
    print(f"Connecting to {dsn} ...")
    db = psycopg2.connect(dsn)

    try:
        # Ensure schema/tables/indexes
        with db.cursor() as cur:
            print("Ensuring schema & tables ...")
            cur.execute(ddl_sql)
        db.commit()

        # Upserts
        with db.cursor() as cur:
            print("Upserting rows ...")
            upsert_core(cur, diseases, synonyms, xrefs, genes, phenos)
        db.commit()

        # Final stats
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ontology.orphanet_diseases")
            n_dis = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ontology.orphanet_gene_links")
            n_gen = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ontology.orphanet_phenotype_links")
            n_phen = cur.fetchone()[0]
        print(f"✅ Done. Counts -> diseases={n_dis:,} genes={n_gen:,} phenotypes={n_phen:,}")

    except Exception as e:
        db.rollback()
        print(f"❌ Database error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
