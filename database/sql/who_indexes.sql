-- Medicines
CREATE INDEX IF NOT EXISTS who_eml_antibiotic_group_idx
  ON guidelines.who_eml_medicines(antibiotic_group);

CREATE INDEX IF NOT EXISTS who_eml_meds_ts_idx
  ON guidelines.who_eml_medicines USING GIN(ts);

-- ATC / ICD11 helpers
CREATE INDEX IF NOT EXISTS who_eml_atc_med_id_idx
  ON guidelines.who_eml_atc(med_id);
CREATE INDEX IF NOT EXISTS who_eml_atc_code_idx
  ON guidelines.who_eml_atc(atc_code);

CREATE INDEX IF NOT EXISTS who_eml_icd11_med_id_idx
  ON guidelines.who_eml_icd11(med_id);
CREATE INDEX IF NOT EXISTS who_eml_icd11_code_idx
  ON guidelines.who_eml_icd11(icd11_code);

-- Committee ANN index (optional; where clause keeps index small)
CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_who_committee
  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 200)
  WHERE source='who_committee';

ANALYZE;
