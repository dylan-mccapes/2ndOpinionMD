#!/usr/bin/env python3
"""
scrub_real_ptv.py
=================

Scrub PII from the real PatientTimelineVision (PTV) graph artifact so that it
can be shared with external collaborators (e.g. Dr. Kaleb Michaud / FORWARD)
as an anatomy example without exposing patient identity.

Source PII inventory (discovered by audit of the file):
  - Patient name (Norman Eric Roberts / Roberts, Norman E / Mr. Roberts / bare
    "Norman" / bare "Roberts")
  - Family member mention (Ken Roberts)
  - MRN (110005992681)
  - DOB (8/17/1947)
  - Phone (925-210-8834)
  - Street address (25 N Via Monte)
  - City + ZIP (Walnut Creek, CA 94598 / plain "Walnut Creek")
  - Facility ("Kaiser Walnut Creek")
  - Provider names attached to vaccine-given entries
  - Source filename (NormanEricRoberts_decrypted_truncated.pdf)

The internal `patient_id` UUID is kept intact because it is a random identifier
minted by 2ndOpinionMD (no link-back to identity without our internal mapping).

Replacements are applied recursively to every string value in the JSON tree.
After scrubbing the output is re-audited for leftover tokens.

Usage
-----
    # Default: full_20260422T143255Z_pretty -> full_20260422T143255Z_scrubbed_pretty
    python server/scripts/scrub_real_ptv.py

    # Custom input / output / audit paths (any absolute or workspace-relative path):
    python server/scripts/scrub_real_ptv.py \
        --input  artifacts/ptv_46860f06-..._indexed_..._v1_noarcs_pretty.json \
        --output artifacts/ptv_46860f06-..._indexed_..._v1_noarcs_scrubbed_pretty.json \
        --audit  artifacts/SCRUB_AUDIT_NOARCS_20260423.txt

Output
------
    <output JSON path>
    <audit text path>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from collections import Counter


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SRC = ROOT / "artifacts" / "ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_pretty.json"
DEFAULT_OUT = ROOT / "artifacts" / "ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_scrubbed_pretty.json"
DEFAULT_AUDIT = ROOT / "artifacts" / "SCRUB_AUDIT_20260423.txt"


# ---------------------------------------------------------------------------
# Replacement table
#
# Order matters: long / specific patterns first so that more general single
# tokens ("Norman", "Roberts") do not pre-empt richer matches.
# ---------------------------------------------------------------------------

Replacement = tuple[re.Pattern[str], str, str]  # (compiled_pattern, replacement, label)


def _p(pattern: str, repl: str, label: str, flags: int = 0) -> Replacement:
    return (re.compile(pattern, flags), repl, label)


# Use (?<![A-Za-z]) / (?![a-z]) instead of \b so that replacements still
# fire when EHR-extracted text runs name tokens up against digits with no
# whitespace (e.g. "925-210-8834Norman" or "94598925"), AND when the banner
# concatenates the name to the next all-caps field (e.g. "RobertsMRN:").
# The right-side lookahead only blocks LOWERCASE alpha so that we don't
# over-match legitimate longer words like "Robertsian" or "Normandy".

_NA = r"(?<![A-Za-z])"  # no alphabetic char immediately to the left
_NZ = r"(?![a-z])"      # no LOWERCASE alpha char immediately to the right

REPLACEMENTS: list[Replacement] = [
    _p(rf"{_NA}Roberts,\s*Norman\s*E\.?{_NZ}",                "[PATIENT]",            "name:lastname_firstname"),
    _p(rf"{_NA}Norman\s+E(?:ric|\.?)\s+Roberts{_NZ}",         "[PATIENT]",            "name:full"),
    _p(rf"{_NA}NormanEricRoberts{_NZ}",                       "[PATIENT]",            "name:squashed"),
    _p(rf"{_NA}Mr\.?\s+Roberts{_NZ}",                         "[PATIENT]",            "name:honorific"),
    _p(rf"{_NA}Ken\s+Roberts{_NZ}",                           "[FAMILY_MEMBER]",      "name:family_member"),
    _p(rf"{_NA}Norman{_NZ}",                                  "[PATIENT]",            "name:first"),
    _p(rf"{_NA}Roberts{_NZ}",                                 "[PATIENT]",            "name:last"),

    _p(r"MRN:\s*110005992681",                                "MRN: [REDACTED]",      "id:mrn_labeled"),
    _p(r"MR\s*#\s*110005992681",                              "MR # [REDACTED]",      "id:mrn_mrhash"),
    _p(r"110005992681",                                       "[MRN_REDACTED]",       "id:mrn_bare"),

    _p(r"DOB:\s*8/17/1947",                                   "DOB: [REDACTED]",      "dob:labeled"),
    _p(r"8/17/1947",                                          "[DOB_REDACTED]",       "dob:bare"),
    # ISO form leaks into event timestamps and index keys because the
    # DOB on page 98 was parsed as a "date found on page" at ingest.
    _p(r"1947-08-17",                                         "[DOB_REDACTED]",       "dob:iso"),

    _p(r"925-210-8834",                                       "[PHONE_REDACTED]",     "phone"),

    # Multi-word address tokens: do not anchor a right-side alpha lookahead,
    # because run-on text like "Via MonteWalnut Creek" has no space between
    # tokens and the lookahead would block the match.
    _p(r"25\s*N\s+Via\s*Monte",                               "[ADDRESS_REDACTED]",        "address:street"),
    _p(r"Via\s*Monte",                                        "[ADDRESS_REDACTED]",        "address:street_partial"),
    _p(r"Walnut\s+Creek,?\s*CA\s*94598",                      "[CITY_STATE_ZIP_REDACTED]", "address:city_state_zip"),
    _p(r"Kaiser\s+Permanente",                                "[FACILITY]",                "facility:kp"),
    _p(r"Kaiser\s+Walnut\s+Creek",                            "[FACILITY]",                "facility:named"),
    _p(rf"{_NA}Kaiser{_NZ}",                                  "[FACILITY]",                "facility:bare"),
    _p(r"Walnut\s+Creek",                                     "[CITY_REDACTED]",           "city:bare"),
    # Trailing "Walnut" at a preview truncation boundary (e.g. "Information[...]Walnut\u2026").
    _p(r"Walnut(?![a-z])",                                    "[CITY_REDACTED]",           "city:trailing"),

    _p(rf"{_NA}Wingo,\s*Alison\s*R\.?{_NZ}",                  "[PROVIDER]",           "provider"),
    _p(rf"{_NA}Maldonado,\s*Eva\s*N\.?{_NZ}",                 "[PROVIDER]",           "provider"),
    _p(rf"{_NA}Burnett,\s*Joanne\s*L\.?{_NZ}",                "[PROVIDER]",           "provider"),
    _p(rf"{_NA}Santos,\s*Christian\s*J\.?{_NZ}",              "[PROVIDER]",           "provider"),
    _p(rf"{_NA}Rojas\s+Mendoza,\s*Jose{_NZ}",                 "[PROVIDER]",           "provider"),
]


# ---------------------------------------------------------------------------
# Recursive tree walker
# ---------------------------------------------------------------------------

def scrub_string(s: str, counter: Counter[str]) -> str:
    out = s
    for pat, repl, label in REPLACEMENTS:
        if pat.search(out):
            out, n = pat.subn(repl, out)
            if n:
                counter[label] += n
    return out


def walk(node, counter: Counter[str]):
    if isinstance(node, dict):
        new = {}
        for k, v in node.items():
            new_k = scrub_string(k, counter) if isinstance(k, str) else k
            new[new_k] = walk(v, counter)
        return new
    if isinstance(node, list):
        return [walk(v, counter) for v in node]
    if isinstance(node, str):
        return scrub_string(node, counter)
    return node


# ---------------------------------------------------------------------------
# Post-scrub audit
# ---------------------------------------------------------------------------

# Audit patterns deliberately use substring matching (no \b) so they catch
# banner run-ons like "RobertsMRN" where a \b-boundary would evade detection.
# Audit patterns deliberately use substring matching (no \b) so they catch
# banner run-ons like "RobertsMRN" where a \b-boundary would evade detection.
AUDIT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Norman",                re.compile(r"Norman")),
    ("Roberts",               re.compile(r"Roberts")),
    ("NormanEricRoberts",     re.compile(r"NormanEricRoberts")),
    ("MRN 110005992681",      re.compile(r"110005992681")),
    ("DOB 8/17/1947",         re.compile(r"8/17/1947")),
    ("DOB 1947-08-17 (ISO)",  re.compile(r"1947-08-17")),
    ("DOB year (1947)",       re.compile(r"1947")),
    ("Phone 925-210-8834",    re.compile(r"925-210-8834")),
    ("Phone 4-digit (8834)",  re.compile(r"8834")),
    ("Via Monte",             re.compile(r"Via\s*Monte")),
    ("Walnut Creek",          re.compile(r"Walnut\s+Creek")),
    ("Walnut (bare)",         re.compile(r"Walnut")),
    ("Kaiser",                re.compile(r"Kaiser")),
    ("Ken Roberts",           re.compile(r"Ken\s+Roberts")),
    ("Wingo",                 re.compile(r"Wingo")),
    ("Maldonado",             re.compile(r"Maldonado")),
    ("Burnett",               re.compile(r"Burnett")),
    ("Santos, Christian",     re.compile(r"Santos,\s*Christian")),
    ("Rojas Mendoza",         re.compile(r"Rojas\s+Mendoza")),
]


def audit(text: str) -> list[tuple[str, int]]:
    results = []
    for label, pat in AUDIT_PATTERNS:
        hits = len(pat.findall(text))
        results.append((label, hits))
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _resolve(p: str | Path) -> Path:
    """Resolve a CLI-provided path: absolute as-is, relative against CWD then ROOT."""
    pth = Path(p)
    if pth.is_absolute():
        return pth
    cwd_candidate = (Path.cwd() / pth).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (ROOT / pth).resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Scrub PII from a PatientTimelineVision (PTV) JSON artifact.",
    )
    ap.add_argument("--input",  "-i", default=str(DEFAULT_SRC),
                    help=f"Input PTV JSON (default: {DEFAULT_SRC.name})")
    ap.add_argument("--output", "-o", default=None,
                    help="Output scrubbed JSON path. "
                         "Default: sibling of input with '_scrubbed' suffix, or "
                         f"{DEFAULT_OUT.name} when using the default input.")
    ap.add_argument("--audit",  "-a", default=None,
                    help="Audit text file path. "
                         "Default: sibling of output as SCRUB_AUDIT_<stem>.txt, or "
                         f"{DEFAULT_AUDIT.name} when using defaults.")
    return ap.parse_args(argv)


def _derive_default_output(src: Path) -> Path:
    """Insert '_scrubbed' before '_pretty' if present, else before the suffix."""
    stem = src.stem
    if stem.endswith("_pretty"):
        new_stem = stem[: -len("_pretty")] + "_scrubbed_pretty"
    else:
        new_stem = stem + "_scrubbed"
    return src.with_name(new_stem + src.suffix)


def _derive_default_audit(out: Path) -> Path:
    return out.with_name(f"SCRUB_AUDIT_{out.stem}.txt")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    src = _resolve(args.input)

    if args.output is not None:
        out = _resolve(args.output)
    elif src.resolve() == DEFAULT_SRC.resolve():
        out = DEFAULT_OUT
    else:
        out = _derive_default_output(src)

    if args.audit is not None:
        audit_path = _resolve(args.audit)
    elif src.resolve() == DEFAULT_SRC.resolve():
        audit_path = DEFAULT_AUDIT
    else:
        audit_path = _derive_default_audit(out)

    if not src.exists():
        print(f"[error] source not found: {src}")
        return 2

    print(f"[0/4] src   : {src}")
    print(f"       out   : {out}")
    print(f"       audit : {audit_path}")

    print(f"[1/4] loading {src.name}  ({src.stat().st_size/1024/1024:.2f} MB)")
    with src.open("r", encoding="utf-8") as fh:
        doc = json.load(fh)

    print("[2/4] walking tree and applying {} replacement rules"
          .format(len(REPLACEMENTS)))
    counter: Counter[str] = Counter()
    scrubbed = walk(doc, counter)

    meta = scrubbed.setdefault("metadata", {})
    lpi = meta.setdefault("last_pdf_ingest", {})
    if "filename" in lpi:
        old = lpi["filename"]
        lpi["filename"] = "patient_record_redacted.pdf"
        counter["source_filename"] += 1
        print(f"       [structural] last_pdf_ingest.filename: '{old}' -> 'patient_record_redacted.pdf'")

    # Structural DOB cleanup: any metadata.patient block + any by_year/by_day
    # index key that encodes 1947 / [DOB_REDACTED] explicitly.
    if "patient" in meta:
        meta["patient"] = {"dob": "[DOB_REDACTED]"}
        counter["structural:patient_dob"] += 1
        print("       [structural] metadata.patient collapsed to {dob: [DOB_REDACTED]}")

    idx = meta.get("index") if isinstance(meta.get("index"), dict) else None
    if isinstance(idx, dict):
        for bucket_name in ("by_year", "by_day", "by_month"):
            bucket = idx.get(bucket_name)
            if not isinstance(bucket, dict):
                continue
            for key in list(bucket.keys()):
                if isinstance(key, str) and (key.startswith("1947") or "[DOB_REDACTED]" in key):
                    bucket.pop(key, None)
                    counter[f"structural:index_{bucket_name}"] += 1

    meta["pii_scrubbed"] = {
        "scrubber": "server/scripts/scrub_real_ptv.py",
        "scrubbed_at": "2026-04-23",
        "rules_applied": len(REPLACEMENTS),
        "replacement_counts_by_label": dict(counter),
    }

    print("[3/4] writing scrubbed output to {}".format(out.name))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(scrubbed, fh, ensure_ascii=False, indent=4)

    print("[4/4] re-auditing scrubbed file for leftover PII tokens")
    scrubbed_text = out.read_text(encoding="utf-8")
    audit_rows = audit(scrubbed_text)
    clean = all(n == 0 for _, n in audit_rows)

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as fh:
        fh.write("PTV PII scrub audit\n")
        fh.write("source   : {}\n".format(src.name))
        fh.write("scrubbed : {}\n".format(out.name))
        fh.write("size     : {:.2f} MB -> {:.2f} MB\n".format(
            src.stat().st_size/1024/1024, out.stat().st_size/1024/1024))
        fh.write("\nReplacement counts (by rule label):\n")
        for label, n in sorted(counter.items(), key=lambda kv: -kv[1]):
            fh.write(f"  {label:<32} {n:>6}\n")
        fh.write("\nPost-scrub leftover scan:\n")
        for label, n in audit_rows:
            fh.write(f"  {label:<32} {n:>6}\n")
        fh.write("\nRESULT: {}\n".format("CLEAN" if clean else "LEFTOVERS FOUND"))

    print("\n--- replacement counts ---")
    for label, n in sorted(counter.items(), key=lambda kv: -kv[1]):
        print(f"  {label:<32} {n:>6}")

    print("\n--- leftover audit ---")
    for label, n in audit_rows:
        flag = " " if n == 0 else "!"
        print(f"{flag} {label:<32} {n:>6}")

    print("\nRESULT: {}".format("CLEAN" if clean else "LEFTOVERS FOUND"))
    print(f"audit written to {audit_path}")
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
