#!/usr/bin/env python3
import argparse, csv, os, sys, re, gzip, io, itertools as it
import psycopg2
from psycopg2.extras import execute_values

# ---------- config ----------
DEFAULT_SOURCE = "CHV"
PAGE_SIZE = 10000

# ---------- DB URL ----------
def get_db_url():
    url = os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd"
    return url.replace("+asyncpg", "")

# ---------- file helpers ----------
def open_maybe_gz(path: str):
    """
    Return a live text stream for the file. If it's gzipped, wrap GzipFile
    around the still-open binary handle. Caller is responsible for closing.
    """
    f = open(path, "rb")
    head = f.read(2)
    f.seek(0)
    if head == b"\x1f\x8b":
        gz = gzip.GzipFile(fileobj=f)
        return io.TextIOWrapper(gz, encoding="utf-8", errors="ignore")
    return io.TextIOWrapper(f, encoding="utf-8", errors="ignore")

def sniff_dialect(sample: str):
    # Prefer tab; fall back to CSV if needed
    try:
        return csv.Sniffer().sniff(sample, delimiters="\t,|")
    except Exception:
        class _ExcelTab(csv.Dialect):
            delimiter = "\t"
            quotechar = '"'
            doublequote = True
            escapechar = None
            lineterminator = "\n"
            quoting = csv.QUOTE_MINIMAL
        return _ExcelTab()

# ---------- heuristics for headerless CHV ----------
CUI_RX = re.compile(r"^C\d{7}$")
NUMBER_LIKE_RX = re.compile(r"^-?\d+(\.\d+)?$")

HEADER_HINTS_CUI = {"cui", "umlscui", "umls_cui", "umlscui"}
HEADER_HINTS_TERM = {"layterm", "term", "string", "name", "label", "display_term"}

def looks_like_term(s: str) -> bool:
    if not s:
        return False
    t = s.strip()
    if not t:
        return False
    lo = t.lower()
    if lo in {"yes", "no", "y", "n"}:
        return False
    if NUMBER_LIKE_RX.match(lo):
        return False
    # at least 2 letters somewhere
    if len(re.sub(r"[^A-Za-z]", "", t)) < 2:
        return False
    return True

def detect_header(first_row):
    """
    Return (has_header, header_lower_list_or_None).
    If any cell looks like a header keyword, treat row as header.
    """
    lower = [c.strip().lower() for c in first_row]
    has = any((h in HEADER_HINTS_CUI) or (h in HEADER_HINTS_TERM) for h in lower)
    return has, (lower if has else None)

def choose_indices(first_row, has_header, header_lower):
    """
    Decide which columns are CUI and TERM.
    If header: use header names; else: use value heuristics on the first data row.
    Returns (cui_idx, term_idx) (possibly None if not found).
    """
    if has_header:
        cui_idx = None
        term_idx = None
        for i, h in enumerate(header_lower):
            if h in HEADER_HINTS_CUI and cui_idx is None:
                cui_idx = i
            if h in HEADER_HINTS_TERM and term_idx is None:
                term_idx = i
        return cui_idx, term_idx

    # No header: value-based heuristics on the first data row
    cui_idx = None
    term_idx = None

    # 1) CUI: first cell like C########
    for i, v in enumerate(first_row):
        if CUI_RX.match((v or "").strip()):
            cui_idx = i
            break

    # 2) TERM: pick the first human-looking text; bias toward early columns
    preferred = [1, 3, 2, 0]  # CHV layouts often put the main term at col1
    ordered = [i for i in preferred if i < len(first_row)] + [i for i in range(len(first_row)) if i not in preferred]
    for i in ordered:
        if i == cui_idx:
            continue
        if looks_like_term(first_row[i]):
            term_idx = i
            break

    return cui_idx, term_idx

# ---------- parsing ----------
def parse_chv(file_path: str):
    """
    Returns (rows, total_rows) where rows is a list of (term, cui)
    """
    # Read small sample for dialect
    sample_fh = open_maybe_gz(file_path)
    try:
        sample = sample_fh.read(65536)
    finally:
        sample_fh.close()

    dialect = sniff_dialect(sample)

    rows = []
    total = 0

    with open_maybe_gz(file_path) as fh:
        reader = csv.reader(fh, dialect)
        try:
            first = next(reader)
        except StopIteration:
            return [], 0

        has_header, header_lower = detect_header(first)
        cui_idx, term_idx = choose_indices(first, has_header, header_lower)

        if has_header:
            data_iter = reader
        else:
            # 'first' is actually a data row
            data_iter = it.chain([first], reader)

        if cui_idx is None or term_idx is None:
            # Show the first row we saw to help debugging
            print("❌ Could not locate required columns. Detected headers:")
            print(first)
            print("Need at least a term column (e.g., layTerm/term) and CUI (e.g., CUI/UMLSCUI).")
            sys.exit(2)

        for row in data_iter:
            total += 1
            if cui_idx >= len(row) or term_idx >= len(row):
                continue
            cui = (row[cui_idx] or "").strip().upper()
            term = (row[term_idx] or "").strip()
            if not (CUI_RX.match(cui) and looks_like_term(term)):
                continue
            rows.append((term, cui))

    return rows, total

# ---------- DB insert ----------
def insert_synonyms(conn, pairs, source=DEFAULT_SOURCE):
    """
    Insert (term, cui) pairs into ontology.synonyms. If the table doesn't
    have a 'source' column, retry without it.
    """
    if not pairs:
        return 0

    with conn.cursor() as cur:
        # First try with source
        try:
            data = [(t, c, source) for t, c in pairs]
            execute_values(
                cur,
                """
                INSERT INTO ontology.synonyms (term, cui, source)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                data,
                page_size=PAGE_SIZE,
            )
            return len(pairs)
        except Exception as e:
            # Retry without source if column doesn't exist
            conn.rollback()
            try:
                execute_values(
                    cur,
                    """
                    INSERT INTO ontology.synonyms (term, cui)
                    VALUES %s
                    ON CONFLICT DO NOTHING
                    """,
                    pairs,
                    page_size=PAGE_SIZE,
                )
                return len(pairs)
            except Exception as e2:
                conn.rollback()
                raise

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="Import Consumer Health Vocabulary (CHV) terms into ontology.synonyms")
    ap.add_argument("--file", required=True, help="Path to CHV concepts_terms file (.tsv or .tsv.gz)")
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="Value to store in synonyms.source (if column exists)")
    ap.add_argument("--dry-run", action="store_true", help="Parse only, do not write to database")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        sys.exit(2)

    print(f"Scanning {args.file} ...")
    pairs, total = parse_chv(args.file)
    uniq = {(t.lower(), c) for t, c in pairs}  # case-insensitive term dedupe, keep CUI exact
    pairs_dedup = [(t, c) for (t, c) in sorted(uniq)]

    print(f"✅ Parsed rows: {total:,}")
    print(f"✅ Candidate pairs: {len(pairs):,}")
    print(f"✅ After dedup: {len(pairs_dedup):,}")

    if args.dry_run:
        print("🔍 DRY RUN: No database writes performed.")
        # show a peek
        for t, c in pairs_dedup[:5]:
            print("  →", repr(t)[:80], c)
        return

    # Insert
    conn = psycopg2.connect(get_db_url())
    try:
        inserted = insert_synonyms(conn, pairs_dedup, source=args.source)
        conn.commit()
        print(f"✅ Inserted (or already present) rows: {inserted:,}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Database error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()

