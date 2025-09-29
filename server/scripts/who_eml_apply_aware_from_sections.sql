UPDATE guidelines.who_eml_medicines
SET antibiotic_group = CASE
  WHEN section_path ILIKE '%access group antibiotics%'  THEN 'Access'
  WHEN section_path ILIKE '%watch group antibiotics%'   THEN 'Watch'
  WHEN section_path ILIKE '%reserve group antibiotics%' THEN 'Reserve'
  ELSE antibiotic_group
END
WHERE COALESCE(antibiotic_group,'') = '';
