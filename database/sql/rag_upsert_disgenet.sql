-- 1) Upsert DisGeNET rows into rag_corpus
INSERT INTO public.rag_corpus (source, title, text, meta)
SELECT
  'disgenet' AS source,
  concat('DG: ', COALESCE(gene_symbol,'?'), ' ↔ ', COALESCE(disease_name,'?')) AS title,
  trim(both ' ' FROM concat_ws(' ',
    'Gene:', gene_symbol,
    '(NCBI:', gene_ncbi_id, ', type:', COALESCE(gene_ncbi_type,''), ')',
    '→ Disease:', disease_name, '('||COALESCE(disease_umls_cui,'')||')',
    'Score:', score::text,
    CASE WHEN num_pmids IS NOT NULL THEN 'PMIDs:'||num_pmids::text ELSE '' END
  )) AS text,
  jsonb_build_object(
    'assoc_id', assoc_id,
    'gene_ncbi_id', gene_ncbi_id,
    'gene_symbol', gene_symbol,
    'disease_umls_cui', disease_umls_cui,
    'disease_name', disease_name,
    'score', score
  ) AS meta
FROM molecular.disgenet_associations d
WHERE NOT EXISTS (
  SELECT 1 FROM public.rag_corpus r
  WHERE r.source = 'disgenet'
    AND (r.meta->>'assoc_id') = d.assoc_id
);

-- 2) Refresh FTS for just these rows
UPDATE public.rag_corpus
SET ts = to_tsvector('english', coalesce(title,'')||' '||coalesce(text,''))
WHERE source = 'disgenet' AND ts IS NULL;

