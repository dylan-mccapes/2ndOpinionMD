-- Backfill functions for MIMIC-IV Notes → HADM mapping (idempotent CREATE OR REPLACE)

-- 1) Unique “within admission window” backfill (updates base table + logs in map)
CREATE OR REPLACE FUNCTION text.backfill_mimiciv_notes_within_window()
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE v_rows int;
BEGIN
  WITH uniq AS (
    SELECT n.note_id, a.hadm_id
    FROM text.mimiciv_notes n
    JOIN ehr_mimic4.admissions a
      ON a.subject_id = n.subject_id
     AND n.charttime >= a.admittime
     AND n.charttime <= a.dischtime
    WHERE n.hadm_id IS NULL
    GROUP BY n.note_id, a.hadm_id
    HAVING COUNT(*) = 1
  ),
  upd AS (
    UPDATE text.mimiciv_notes n
       SET hadm_id = u.hadm_id
      FROM uniq u
     WHERE n.note_id = u.note_id
       AND n.hadm_id IS NULL
    RETURNING n.note_id, u.hadm_id
  )
  INSERT INTO text.mimiciv_notes_hadm_map (note_id, hadm_id, method, dt_seconds)
  SELECT note_id, hadm_id, 'within_window', NULL
  FROM upd
  ON CONFLICT (note_id, method) DO NOTHING;

  GET DIAGNOSTICS v_rows = ROW_COUNT;
  RETURN v_rows;
END
$$;

-- 2) Unique “within transfer window” backfill (updates base table + logs)
CREATE OR REPLACE FUNCTION text.backfill_mimiciv_notes_within_transfer()
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE v_rows int;
BEGIN
  WITH cand AS (
    SELECT n.note_id, t.hadm_id,
           COUNT(*) OVER (PARTITION BY n.note_id) AS k
    FROM text.mimiciv_notes n
    JOIN ehr_mimic4.transfers t
      ON t.subject_id = n.subject_id
     AND n.charttime BETWEEN t.intime AND t.outtime
    WHERE n.hadm_id IS NULL AND n.charttime IS NOT NULL
  ),
  uniq AS (
    SELECT note_id, hadm_id FROM cand WHERE k = 1
  ),
  upd AS (
    UPDATE text.mimiciv_notes n
       SET hadm_id = u.hadm_id
      FROM uniq u
     WHERE n.note_id = u.note_id
       AND n.hadm_id IS NULL
    RETURNING n.note_id, u.hadm_id
  )
  INSERT INTO text.mimiciv_notes_hadm_map (note_id, hadm_id, method, dt_seconds)
  SELECT note_id, hadm_id, 'within_transfer', NULL
  FROM upd
  ON CONFLICT (note_id, method) DO NOTHING;

  GET DIAGNOSTICS v_rows = ROW_COUNT;
  RETURN v_rows;
END
$$;

-- 3) “nearest N hours to admission window edge” (updates base table + logs)
CREATE OR REPLACE FUNCTION text.backfill_mimiciv_notes_nearest(p_hours int DEFAULT 48)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE v_rows int;
BEGIN
  WITH multi AS (
    SELECT n.note_id,
           a.hadm_id,
           CASE
             WHEN n.charttime < a.admittime THEN EXTRACT(EPOCH FROM (a.admittime - n.charttime))
             WHEN n.charttime > a.dischtime THEN EXTRACT(EPOCH FROM (n.charttime - a.dischtime))
             ELSE 0
           END::int AS dt_sec,
           ROW_NUMBER() OVER (
             PARTITION BY n.note_id
             ORDER BY
               CASE
                 WHEN n.charttime < a.admittime THEN EXTRACT(EPOCH FROM (a.admittime - n.charttime))
                 WHEN n.charttime > a.dischtime THEN EXTRACT(EPOCH FROM (n.charttime - a.dischtime))
                 ELSE 0
               END
           ) AS rn
    FROM text.mimiciv_notes n
    JOIN ehr_mimic4.admissions a
      ON a.subject_id = n.subject_id
    WHERE n.hadm_id IS NULL
      AND n.charttime IS NOT NULL
  ),
  pick AS (
    SELECT note_id, hadm_id, dt_sec
    FROM multi
    WHERE rn = 1 AND dt_sec <= p_hours * 3600
  ),
  upd AS (
    UPDATE text.mimiciv_notes n
       SET hadm_id = p.hadm_id
      FROM pick p
     WHERE n.note_id = p.note_id
       AND n.hadm_id IS NULL
    RETURNING n.note_id, p.hadm_id, p.dt_sec
  )
  INSERT INTO text.mimiciv_notes_hadm_map (note_id, hadm_id, method, dt_seconds)
  SELECT note_id, hadm_id, format('nearest_%sh', p_hours), dt_sec
  FROM upd
  ON CONFLICT (note_id, method) DO UPDATE
    SET hadm_id    = EXCLUDED.hadm_id,
        dt_seconds = EXCLUDED.dt_seconds;

  GET DIAGNOSTICS v_rows = ROW_COUNT;
  RETURN v_rows;
END
$$;

-- 4) Map-only “nearest N hours” (does NOT update base table; just records best candidate)
CREATE OR REPLACE FUNCTION text.map_mimiciv_notes_nearest_only(p_hours int DEFAULT 168)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE v_rows int;
BEGIN
  WITH multi AS (
    SELECT n.note_id,
           a.hadm_id,
           CASE
             WHEN n.charttime < a.admittime THEN EXTRACT(EPOCH FROM (a.admittime - n.charttime))
             WHEN n.charttime > a.dischtime THEN EXTRACT(EPOCH FROM (n.charttime - a.dischtime))
             ELSE 0
           END::int AS dt_sec,
           ROW_NUMBER() OVER (
             PARTITION BY n.note_id
             ORDER BY
               CASE
                 WHEN n.charttime < a.admittime THEN EXTRACT(EPOCH FROM (a.admittime - n.charttime))
                 WHEN n.charttime > a.dischtime THEN EXTRACT(EPOCH FROM (n.charttime - a.dischtime))
                 ELSE 0
               END
           ) AS rn
    FROM text.mimiciv_notes n
    JOIN ehr_mimic4.admissions a
      ON a.subject_id = n.subject_id
    WHERE n.charttime IS NOT NULL
  ),
  pick AS (
    SELECT note_id, hadm_id, dt_sec
    FROM multi
    WHERE rn = 1 AND dt_sec <= p_hours * 3600
  )
  INSERT INTO text.mimiciv_notes_hadm_map (note_id, hadm_id, method, dt_seconds)
  SELECT note_id, hadm_id, format('nearest_only_%sh', p_hours), dt_sec
  FROM pick
  ON CONFLICT (note_id, method) DO UPDATE
    SET hadm_id    = EXCLUDED.hadm_id,
        dt_seconds = EXCLUDED.dt_seconds;

  GET DIAGNOSTICS v_rows = ROW_COUNT;
  RETURN v_rows;
END
$$;

