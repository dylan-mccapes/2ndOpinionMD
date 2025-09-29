-- Ensure table exists
CREATE TABLE IF NOT EXISTS guidelines.who_aware_map (
  atc_code   text PRIMARY KEY,
  group_name text,
  src        text,
  raw        jsonb,
  updated_at timestamptz DEFAULT now()
);

-- If older columns existed, coalesce them into group_name once
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='guidelines' AND table_name='who_aware_map' AND column_name='group_name'
  ) THEN
    ALTER TABLE guidelines.who_aware_map ADD COLUMN group_name text;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='guidelines' AND table_name='who_aware_map' AND column_name='"group"'
  ) THEN
    EXECUTE 'UPDATE guidelines.who_aware_map SET group_name = COALESCE(group_name, "group") WHERE group_name IS NULL';
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='guidelines' AND table_name='who_aware_map' AND column_name='aware_group'
  ) THEN
    UPDATE guidelines.who_aware_map SET group_name = COALESCE(group_name, aware_group) WHERE group_name IS NULL;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='guidelines' AND table_name='who_aware_map' AND column_name='category'
  ) THEN
    UPDATE guidelines.who_aware_map SET group_name = COALESCE(group_name, category) WHERE group_name IS NULL;
  END IF;
END $$;

-- Make sure atc_code is unique (PRIMARY KEY above already enforces it)
CREATE UNIQUE INDEX IF NOT EXISTS who_aware_map_atc_code_uidx
  ON guidelines.who_aware_map(atc_code);

-- Helpful index
CREATE INDEX IF NOT EXISTS who_aware_group_idx
  ON guidelines.who_aware_map(group_name);
