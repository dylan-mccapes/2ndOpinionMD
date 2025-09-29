ALTER TABLE guidelines.who_aware_map
  ADD COLUMN IF NOT EXISTS src        text,
  ADD COLUMN IF NOT EXISTS raw        jsonb,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

-- Keep the helpful indexes
CREATE UNIQUE INDEX IF NOT EXISTS who_aware_map_atc_code_uidx
  ON guidelines.who_aware_map(atc_code);

CREATE INDEX IF NOT EXISTS who_aware_group_idx
  ON guidelines.who_aware_map(group_name);

