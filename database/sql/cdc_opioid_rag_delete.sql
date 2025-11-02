-- Remove previously inserted CDC rows from RAG (for a clean re-run)
DELETE FROM public.rag_corpus WHERE source = 'cdc_opioid';

