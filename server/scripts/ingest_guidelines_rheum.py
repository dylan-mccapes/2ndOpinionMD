#!/usr/bin/env python
import os
import json
from pathlib import Path

import psycopg
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parents[2]  # repo root
GUIDE_DIR = BASE_DIR / "data" / "guidelines"

# Use same DSN strategy as the rest of the stack
SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"),
)

# One row per guideline family; each will become its own rag_corpus.source
GUIDELINES = [
    {
        "source": "acr_ra_2021",
        "file": "ra-guideline-2021.pdf",
        "title_prefix": "ACR 2021 Guideline for the Treatment of Rheumatoid Arthritis",
        "topic": "rheumatoid_arthritis",
        "society": "ACR",
        "year": 2021,
        "url": "https://assets.contentstack.io/v3/assets/bltee37abb6b278ab2c/blt9e44ccb701e1918c/63360f6775c0be225b8d943a/ra-guideline-2021.pdf",
    },
    {
        "source": "eular_ra_2022",
        "file": "eular-ra-management-2022.pdf",
        "title_prefix": "EULAR 2022 Recommendations for the Management of Rheumatoid Arthritis",
        "topic": "rheumatoid_arthritis",
        "society": "EULAR",
        "year": 2022,
        "url": "https://ard.bmj.com/content/81/10/1358.full.pdf",
    },
    {
        "source": "eular_acr_sle_2019",
        "file": "eular-acr-2019-sle-classification.pdf",
        "title_prefix": "2019 EULAR/ACR Classification Criteria for Systemic Lupus Erythematosus",
        "topic": "sle_classification",
        "society": "EULAR/ACR",
        "year": 2019,
        "url": "https://eprints.whiterose.ac.uk/id/eprint/151919/",
    },
    {
        # Note: filename label says "eular-2025-sle-nephritis" but this URL
        # is actually the ESC/ERS PH guideline; keep topic accurate in meta.
        "source": "esc_ers_ph_2022",
        "file": "eular-2025-sle-nephritis.pdf",
        "title_prefix": "2022 ESC/ERS Guidelines for the Diagnosis and Treatment of Pulmonary Hypertension",
        "topic": "pulmonary_hypertension",
        "society": "ESC/ERS",
        "year": 2022,
        "url": "https://www.portailvasculaire.fr/sites/default/files/docs/2022_esc_ers_guidelines_htp_traitement.pdf",
    },
    {
        "source": "kdigo_gn_ln_2021",
        "file": "kdigo-2021-glomerular-diseases.pdf",
        "title_prefix": "KDIGO 2021 Glomerular Diseases Guideline (Lupus Nephritis Update 2024)",
        "topic": "glomerular_disease_lupus_nephritis",
        "society": "KDIGO",
        "year": 2021,
        "url": "https://kdigo.org/wp-content/uploads/2017/02/KDIGO-2021-Glomerular-Diseases-Guideline_English_LN-2024-Update.pdf",
    },
    {
        "source": "acr_ild_2023",
        "file": "acr-2023-ild-treatment.pdf",
        "title_prefix": "ACR 2023 Guideline: ILD in Systemic Autoimmune Rheumatic Diseases",
        "topic": "sard_interstitial_lung_disease",
        "society": "ACR",
        "year": 2023,
        "url": "https://assets.contentstack.io/v3/assets/bltee37abb6b278ab2c/bltffeaff36ede96636/interstitial-lung-disease-guideline-screening-monitoring-2023.pdf",
    },
    {
        "source": "nice_ta397_belimumab",
        "file": "nice-ta397-belimumab.pdf",
        "title_prefix": "NICE TA397: Belimumab for Treating Active Autoantibody-Positive SLE",
        "topic": "sle_belimumab_technology_appraisal",
        "society": "NICE",
        "year": 2016,
        "url": "https://www.nice.org.uk/guidance/ta397",
    },
]


def extract_pages(doc_cfg):
    pdf_path = GUIDE_DIR / doc_cfg["file"]
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    reader = PdfReader(str(pdf_path))
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if not text:
            continue

        title = f"{doc_cfg['title_prefix']} – page {idx}"
        meta = {
            "guideline_source": doc_cfg["source"],
            "file_name": doc_cfg["file"],
            "page": idx,
            "topic": doc_cfg["topic"],
            "society": doc_cfg["society"],
            "year": doc_cfg["year"],
            "url": doc_cfg["url"],
        }

        yield {
            "source": doc_cfg["source"],
            "source_id": f"{doc_cfg['source']}:p{idx:04d}",
            "title": title,
            "text": text,
            "meta": meta,
        }


def main():
    conn = psycopg.connect(SYNC_DATABASE_URL, autocommit=True)
    cur = conn.cursor()

    # Make sure ts exists; embedding stays NULL for now and will be filled
    # by your existing async embed pipeline.
    sql = """
        INSERT INTO rag_corpus (source, source_id, title, text, meta, ts)
        VALUES (%(source)s, %(source_id)s, %(title)s, %(text)s, %(meta)s::jsonb,
                to_tsvector('english', %(ts_body)s))
        ON CONFLICT (source, source_id) DO UPDATE
        SET title = EXCLUDED.title,
            text  = EXCLUDED.text,
            meta  = EXCLUDED.meta,
            ts    = EXCLUDED.ts;
    """

    total = 0
    for doc in GUIDELINES:
        for row in extract_pages(doc):
            ts_body = f"{row['title']}\n\n{row['text']}"
            params = {
                "source": row["source"],
                "source_id": row["source_id"],
                "title": row["title"],
                "text": row["text"],
                "meta": json.dumps(row["meta"]),
                "ts_body": ts_body,
            }
            cur.execute(sql, params)
            total += 1
            if total % 100 == 0:
                print(f"...inserted {total} guideline pages")

    print(f"Done. Inserted/updated ~{total} guideline page rows.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

