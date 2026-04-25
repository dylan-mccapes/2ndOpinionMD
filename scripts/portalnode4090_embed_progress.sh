#!/usr/bin/env bash
# Show rag_corpus.local embed progress while embed_rag_corpus_local_slice.py runs.
# Uses the same connection env as portalnode4090_embed_rag_slice.sh.
#
#   export SYNC_DATABASE_URL='postgresql://portalnode:PASS@127.0.0.1:5432/portalnode'
#   ./scripts/portalnode4090_embed_progress.sh
#
# Re-run every 30s (another ssh session on PN0):
#   watch -n 30 ./scripts/portalnode4090_embed_progress.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${SYNC_DATABASE_URL:-}" ]]; then
  if [[ -n "${DATABASE_URL:-}" ]]; then
    export SYNC_DATABASE_URL="$DATABASE_URL"
  elif [[ -n "${PGUSER:-}" && -n "${PGDATABASE:-}" ]]; then
    _h="${PGHOST:-127.0.0.1}"
    _p="${PGPORT:-5432}"
    if [[ -n "${PGPASSWORD:-}" ]]; then
      export SYNC_DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${_h}:${_p}/${PGDATABASE}"
    else
      export SYNC_DATABASE_URL="postgresql://${PGUSER}@${_h}:${_p}/${PGDATABASE}"
    fi
  fi
fi
if [[ -z "${SYNC_DATABASE_URL:-}" ]]; then
  echo "Set SYNC_DATABASE_URL, or DATABASE_URL, or PGUSER+PGDATABASE (+ PGPASSWORD)." >&2
  exit 1
fi

psql "$SYNC_DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
\x off
\timing off

SELECT 'rag_corpus embedding_local progress' AS section;

SELECT
  COUNT(*)::bigint AS total_rows,
  COUNT(embedding_local)::bigint AS embedded,
  (COUNT(*) - COUNT(embedding_local))::bigint AS remaining,
  ROUND(100.0 * COUNT(embedding_local) / NULLIF(COUNT(*), 0), 2) AS pct_done
FROM public.rag_corpus;

SELECT 'last batch (heartbeat)' AS section;

SELECT
  (SELECT MAX(embedding_local_at)
   FROM public.rag_corpus
   WHERE embedding_local IS NOT NULL) AS last_embed_at_utc,
  (SELECT embedding_local_model
   FROM public.rag_corpus
   WHERE embedding_local IS NOT NULL
   ORDER BY embedding_local_at DESC NULLS LAST
   LIMIT 1) AS model;

SELECT 'next pending id (script scans by id ASC)' AS section;

SELECT MIN(id) AS next_id_pending
FROM public.rag_corpus
WHERE embedding_local IS NULL;

SELECT 'top sources still pending' AS section;

SELECT
  source,
  COUNT(*) AS n_total,
  COUNT(embedding_local) AS n_done,
  COUNT(*) FILTER (WHERE embedding_local IS NULL) AS n_pending
FROM public.rag_corpus
GROUP BY 1
HAVING COUNT(*) FILTER (WHERE embedding_local IS NULL) > 0
ORDER BY n_pending DESC
LIMIT 15;
SQL

echo ""
echo "Tip: watch -n 30 $ROOT/scripts/portalnode4090_embed_progress.sh"
echo "Python embedder logs: updated N rows (~X rows/s) last_id=..."
