-- Project WHO EML 2025 into RAG
INSERT INTO public.rag_corpus (source, title, text, ts)
SELECT 'who_eml',
       'WHO EML 2025: '||m.inn,
       trim(both ' ' FROM concat_ws(' ',
         'INN:'||m.inn,
         COALESCE('Section:'||m.section_path, ''),
         COALESCE('AWaRe:'||m.antibiotic_group, ''),
         COALESCE('ATC:'||string_agg(DISTINCT a.atc_code, '; '), ''),
         COALESCE('ICD11:'||string_agg(DISTINCT i.icd11_code, '; '), ''),
         COALESCE('Forms:'||string_agg(DISTINCT f.dose_form, '; '), ''),
         COALESCE('Alts:'||string_agg(DISTINCT al.alt_inn, '; '), '')
       )),
       to_tsvector('english', m.inn||' '||coalesce(m.section_path,'')||' '||coalesce(m.antibiotic_group,''))
FROM guidelines.who_eml_medicines m
LEFT JOIN guidelines.who_eml_atc a ON a.med_id=m.med_id
LEFT JOIN guidelines.who_eml_icd11 i ON i.med_id=m.med_id
LEFT JOIN guidelines.who_eml_formulations f ON f.med_id=m.med_id
LEFT JOIN guidelines.who_eml_alternatives al ON al.med_id=m.med_id
GROUP BY m.med_id
HAVING NOT EXISTS (
  SELECT 1 FROM public.rag_corpus rc
  WHERE rc.source='who_eml' AND rc.title='WHO EML 2025: '||m.inn
);

