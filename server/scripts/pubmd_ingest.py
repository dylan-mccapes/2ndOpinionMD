#!/usr/bin/env python3
import os, sys, gzip, json, argparse, datetime, re
from pathlib import Path
from typing import Iterable, List, Dict, Optional, Tuple
import xml.etree.ElementTree as ET
import psycopg

# --------------------- helpers ---------------------

NS_NONE = ""  # PubMed baseline/update XMLs are not namespace-qualified
TEXT = lambda x: (x or "").strip()

def _find(el, path):
    return el.find(path)

def _findall(el, path):
    return el.findall(path)

def parse_pubdate(cit) -> Tuple[Optional[int], Optional[str]]:
    # MedlineCitation/Article/Journal/JournalIssue/PubDate has Year/Month/Day or MedlineDate
    pub = _find(cit, "./Article/Journal/JournalIssue/PubDate")
    if pub is None: return None, None
    year = _find(pub, "Year")
    medline = _find(pub, "MedlineDate")
    y = None
    if year is not None and TEXT(year):
        try: y = int(TEXT(year))
        except: pass
    # coarse YYYY-MM-DD if present
    mm = _find(pub, "Month")
    dd = _find(pub, "Day")
    if y and mm is not None and dd is not None:
        mtxt, dtxt = TEXT(mm), TEXT(dd)
        # Month can be numeric or short name; keep as simple ISO when possible
        if re.fullmatch(r"\d{1,2}", mtxt) and re.fullmatch(r"\d{1,2}", dtxt):
            try:
                d = datetime.date(y, int(mtxt), int(dtxt))
                return y, d.isoformat()
            except: pass
    # fallback—just the year
    return y, None

def join_abstract(cit) -> str:
    parts = []
    for ab in _findall(cit, "./Article/Abstract/AbstractText"):
        txt = "".join(ab.itertext()).strip()
        if txt:
            label = ab.attrib.get("Label")
            if label:
                parts.append(f"{label}: {txt}")
            else:
                parts.append(txt)
    return "\n\n".join(parts).strip()

def gather_mesh(cit) -> List[str]:
    out = []
    for mh in _findall(cit, "./MeshHeadingList/MeshHeading/DescriptorName"):
        t = TEXT(mh)
        if t: out.append(t)
    return out

def gather_authors(cit) -> Tuple[List[str], List[str]]:
    names, affs = [], []
    for a in _findall(cit, "./Article/AuthorList/Author"):
        last = TEXT(_find(a, "LastName"))
        fore = TEXT(_find(a, "ForeName"))
        coll = TEXT(_find(a, "CollectiveName"))
        nm = coll or " ".join(p for p in [fore, last] if p).strip()
        if nm: names.append(nm)
        for af in _findall(a, "AffiliationInfo/Affiliation"):
            t = TEXT(af)
            if t: affs.append(t)
    return names, affs

def pmids_from_file(fp: Path) -> Iterable[ET.Element]:
    # stream parse
    openf = gzip.open if fp.suffix == ".gz" else open
    with openf(fp, "rb") as f:
        ctx = ET.iterparse(f, events=("end",))
        for ev, el in ctx:
            if el.tag.endswith("PubmedArticle"):
                yield el
                el.clear()

def article_from_xml(article: ET.Element) -> Dict:
    cit = _find(article, "./MedlineCitation")
    if cit is None: return {}
    pmid_el = _find(cit, "PMID")
    if pmid_el is None or not TEXT(pmid_el): return {}
    pmid = int(TEXT(pmid_el))

    art = _find(cit, "Article")
    title = "".join(_find(art, "ArticleTitle").itertext()).strip() if art is not None and _find(art, "ArticleTitle") is not None else ""
    abstract = join_abstract(cit)
    journal = TEXT(_find(art, "Journal/Title")) if art is not None else ""
    iso_j = TEXT(_find(art, "Journal/ISOAbbreviation")) if art is not None else ""
    pub_year, pub_date = parse_pubdate(cit)

    # ids
    doi, pmcid = None, None
    for aid in _findall(art, "ELocationID"):
        if aid.attrib.get("EIdType") == "doi":
            doi = TEXT(aid) or doi
    for aid in _findall(article, "./PubmedData/ArticleIdList/ArticleId"):
        typ = aid.attrib.get("IdType")
        if typ == "doi": doi = TEXT(aid) or doi
        if typ == "pmc": pmcid = TEXT(aid) or pmcid

    # types / languages
    types = [TEXT(x) for x in _findall(art, "PublicationTypeList/PublicationType")] if art is not None else []
    langs = [TEXT(x) for x in _findall(art, "Language")] if art is not None else []

    mesh = gather_mesh(cit)
    authors, affs = gather_authors(cit)

    return {
        "pmid": pmid,
        "pmcid": pmcid,
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "journal": journal,
        "iso_journal": iso_j,
        "pub_year": pub_year,
        "pub_date": pub_date,
        "article_types": [x for x in types if x],
        "languages": [x for x in langs if x],
        "license": None,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "has_fulltext": bool(pmcid),
        "mesh_terms": mesh,
        "authors": authors,
        "affiliations": affs,
        "meta": {},
    }

def chunk_text(s: str, size: int, overlap: int) -> List[str]:
    s = (s or "").strip()
    if not s: return []
    out = []
    i = 0
    while i < len(s):
        out.append(s[i:i+size])
        if len(s) <= i+size: break
        i = i + size - overlap
    return out

# --------------------- DB ops ---------------------

def upsert_article(cur, a: Dict):
    cur.execute("""
        INSERT INTO library.pubmd_article
            (pmid, pmcid, doi, title, abstract, journal, iso_journal,
             pub_year, pub_date, article_types, languages, license, url,
             has_fulltext, mesh_terms, authors, affiliations, meta)
        VALUES (%(pmid)s, %(pmcid)s, %(doi)s, %(title)s, %(abstract)s, %(journal)s, %(iso_journal)s,
                %(pub_year)s, %(pub_date)s, %(article_types)s, %(languages)s, %(license)s, %(url)s,
                %(has_fulltext)s, %(mesh_terms)s, %(authors)s, %(affiliations)s, %(meta)s)
        ON CONFLICT (pmid) DO UPDATE SET
            pmcid=EXCLUDED.pmcid, doi=EXCLUDED.doi, title=EXCLUDED.title, abstract=EXCLUDED.abstract,
            journal=EXCLUDED.journal, iso_journal=EXCLUDED.iso_journal, pub_year=EXCLUDED.pub_year,
            pub_date=EXCLUDED.pub_date, article_types=EXCLUDED.article_types, languages=EXCLUDED.languages,
            license=EXCLUDED.license, url=EXCLUDED.url, has_fulltext=EXCLUDED.has_fulltext,
            mesh_terms=EXCLUDED.mesh_terms, authors=EXCLUDED.authors, affiliations=EXCLUDED.affiliations,
            meta=library.pubmd_article.meta || EXCLUDED.meta
    """, a)

def delete_pubmd_chunks_for(cur, pmid: int):
    cur.execute("DELETE FROM rag_corpus WHERE source='pubmd' AND meta->>'pmid' = %s", (str(pmid),))

def insert_pubmd_chunks(cur, a: Dict, chunk_chars: int, overlap: int):
    pieces = []
    # title + abstract is a strong baseline; fulltext (if you add later) can join here
    if a.get("abstract"):
        pieces.append(("abstract", a["abstract"]))
    # (optionally later) if you ingest full text into library.pubmd_fulltex_
