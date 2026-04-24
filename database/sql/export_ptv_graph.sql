-- Compact PTV export (single-line JSON per row) for scp / jq / Python.
--
--   psql "$POSTGRES_DSN" -v ON_ERROR_STOP=1 -t -A -v pid=428b017a-3840-490c-8a95-65c4d6cfe10d \
--     -f database/sql/export_ptv_graph.sql -o ptv_428b017a.json
--
-- Prefer this over SELECT jsonb_pretty(graph_json) when copying files off the server.

SELECT graph_json::text
FROM ehr.patient_graph_vision
WHERE patient_id = :'pid';
