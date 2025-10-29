-- Clear bad values like R2022
UPDATE guidelines.cdc_sections
SET rec_number = NULL
WHERE rec_number ~ '^R[0-9]{3,}$';

-- Extract R# only when 'Recommendation' is nearby and the number is 1-2 digits
UPDATE guidelines.cdc_sections
SET rec_number = 'R' || (regexp_match(heading, '(?i)\\bRecommendation(?:s)?\\s*(?:#|No\\.|Number\\s*)?(\\d{1,2})\\b'))[1]
WHERE heading ~* '\\bRecommendation'
  AND (regexp_match(heading, '(?i)\\bRecommendation(?:s)?\\s*(?:#|No\\.|Number\\s*)?(\\d{1,2})\\b')) IS NOT NULL;

-- As a fallback, try the start of the section HTML header if heading was sparse
UPDATE guidelines.cdc_sections
SET rec_number = 'R' || (regexp_match(text_html, '(?i)Recommendation(?:s)?\\s*(?:#|No\\.|Number\\s*)?(\\d{1,2})\\b'))[1]
WHERE rec_number IS NULL
  AND text_html ~* 'Recommendation';

