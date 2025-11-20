-- Upsert RxNorm concepts into rag_corpus
-- Prefers RXNORM|ISPREF=Y label; falls back to any label.
WITH c AS (
  SELECT rxcui, sab, tty, str, ispref
  FROM ontology.rxnorm_conso
),
pick AS (
  SELECT
    rxcui,
    COALESCE(
      MAX(str) FILTER (WHERE sab = 'RXNORM' AND ispref = 'Y'),
      MAX(str) FILTER (WHERE ispref = 'Y'),
      MAX(str)
    ) AS base_title
  FROM c
  GROUP BY rxcui
),
tty_roll AS (
  SELECT rxcui, array_agg(DISTINCT tty ORDER BY tty) AS ttys
  FROM c
  GROUP BY rxcui
),
ndc_roll AS (
  SELECT rxcui, array_agg(DISTINCT ndc_norm ORDER BY ndc_norm) AS ndcs
  FROM ontology.rxnorm_ndc
  GROUP BY rxcui
),
prep AS (
  SELECT
    'rxnorm'::text       AS source,
    p.rxcui::text        AS source_id,

    -- 🔍 Make RxCUI visible in the title
    (p.base_title || ' [RxCUI ' || p.rxcui::text || ']') AS title,

    -- 📄 Rich text: title + TTYs + NDCs (all with CUI visible at top)
    CONCAT_WS(E'\n',
      (p.base_title || ' [RxCUI ' || p.rxcui::text || ']'),
      CASE WHEN t.ttys IS NOT NULL
           THEN 'TTYs: ' || array_to_string(t.ttys, ', ')
      END,
      CASE WHEN n.ndcs IS NOT NULL
           THEN 'NDCs: ' || array_to_string(n.ndcs, ', ')
      END
    ) AS text,

    -- 🧠 Full-text search vector also includes the CUI string
    to_tsvector(
      'english',
      CONCAT_WS(' ',
        p.base_title,
        p.rxcui::text,
        COALESCE(array_to_string(t.ttys, ' '), ''),
        COALESCE(array_to_string(n.ndcs, ' '), '')
      )
    ) AS ts
  FROM pick p
  LEFT JOIN tty_roll t USING (rxcui)
  LEFT JOIN ndc_roll n USING (rxcui)
)
INSERT INTO public.rag_corpus (source, source_id, title, text, ts)
SELECT source, source_id, title, text, ts
FROM prep
ON CONFLICT (source, source_id) DO UPDATE
SET title = EXCLUDED.title,
    text  = EXCLUDED.text,
    ts    = EXCLUDED.ts;
