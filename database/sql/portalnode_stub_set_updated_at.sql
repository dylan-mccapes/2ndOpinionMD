-- Mac MKG: generic BEFORE UPDATE trigger helper for updated_at (referenced from multiple schemas).
-- Slice pg_dumps often emit CREATE TRIGGER ... EXECUTE FUNCTION _set_updated_at() without this definition.
-- Runs before 02 so ehr/eoh/b2b/guidelines/rag DDL can attach triggers.

CREATE OR REPLACE FUNCTION public._set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = TG_TABLE_SCHEMA
      AND c.table_name = TG_TABLE_NAME
      AND c.column_name = 'updated_at'
  ) THEN
    NEW.updated_at := clock_timestamp();
  END IF;
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public._set_updated_at() IS 'Pilot stub: satisfies updated_at triggers from origin dumps; see portalnode4090_restore_mkg.sh.';
