#!/usr/bin/env bash
set -euo pipefail

# How many evals to run (ignored if EVAL_ID_OVERRIDE is set)
N="${N:-5}"

DB="${PGDATABASE:-2ndopinionmd}"
API_BASE="${API_BASE:-https://2ndopinionmd.ai}"
OUTDIR="${MIMIC_CODING_EVAL_DIR:-/tmp/mimic_coding_eval}"
MAX_Q_LEN="${MAX_Q_LEN:-2800}"      # max length for query_text
USE_VALYU="${USE_VALYU:-1}"         # 1 = use Valyu, 0 = no Valyu

# 1 = only choose evals with ICD-10 gold
# When USE_NOTE_GOLD=1 this means "only eval_ids with nonempty gold_icd10_codes in eval.coding_eval_note_gold"
ICD10_ONLY="${ICD10_ONLY:-1}"

# 1 = sample ONLY eval_ids that have curated note-level gold in eval.coding_eval_note_gold
# 0 = fall back to legacy behavior (encounter-level gold via eval.coding_eval_icd10_results)
USE_NOTE_GOLD="${USE_NOTE_GOLD:-1}"

EVAL_ID_OVERRIDE="${EVAL_ID_OVERRIDE:-}"

mkdir -p "${OUTDIR}"

echo "Running up to ${N} MIMIC coding evals..."
echo "DB: ${DB}"
echo "API: ${API_BASE}"
echo "Output dir: ${OUTDIR}"
echo "MAX_Q_LEN: ${MAX_Q_LEN}"
echo "USE_NOTE_GOLD: ${USE_NOTE_GOLD}"
if [[ -n "${EVAL_ID_OVERRIDE}" ]]; then
  echo "EVAL_ID_OVERRIDE: ${EVAL_ID_OVERRIDE}"
fi
if [[ "${ICD10_ONLY}" = "1" ]]; then
  echo "ICD10_ONLY: 1 (restricting to evals with ICD-10 gold)"
fi
echo "USE_VALYU: ${USE_VALYU}"

# ---------------------------------------------------------------------------
# 1) Choose eval_ids
# ---------------------------------------------------------------------------

eval_ids=""

if [[ -n "${EVAL_ID_OVERRIDE}" ]]; then
  # Single eval_id, no randomness
  eval_ids="${EVAL_ID_OVERRIDE}"
else
  # Build SQL to sample eval_ids
  if [[ "${USE_NOTE_GOLD}" = "1" ]]; then
    # ------------------------------
    # Option A: NOTE-LEVEL GOLD
    # ------------------------------
    # We join eval.coding_eval_queries_mimic4 (note text) to
    # eval.coding_eval_note_gold (curated note-level ICD-10-CM codes)
    # and sample from that universe.
    if [[ "${ICD10_ONLY}" = "1" ]]; then
      read -r -d '' SQL_QUERY <<SQL || true
SELECT eval_id
FROM eval.coding_eval_queries_mimic4
WHERE eval_id IN (
  SELECT eval_id FROM eval.coding_eval_icd10_results
)
  AND length(note_text) <= ${MAX_Q_LEN}
ORDER BY random()
LIMIT ${N};
SQL
    else
      read -r -d '' SQL_QUERY <<SQL || true
SELECT q.eval_id
FROM eval.coding_eval_queries_mimic4 AS q
JOIN eval.coding_eval_note_gold AS g
  ON g.eval_id = q.eval_id
WHERE length(q.note_text) <= ${MAX_Q_LEN}
ORDER BY random()
LIMIT ${N};
SQL
    fi
  else
    # ------------------------------
    # Legacy behavior (encounter-level gold)
    # ------------------------------
    if [[ "${ICD10_ONLY}" = "1" ]]; then
      # Restrict to eval_ids that have ICD-10 gold codes at encounter level
      read -r -d '' SQL_QUERY <<SQL || true
SELECT eval_id
FROM eval.coding_eval_queries_mimic4
WHERE eval_id IN (
  SELECT eval_id FROM eval.coding_eval_icd10_results
)
  AND length(note_text) <= ${MAX_Q_LEN}
ORDER BY random()
LIMIT ${N};
SQL
    else
      # Any eval, just apply length filter
      read -r -d '' SQL_QUERY <<SQL || true
SELECT eval_id
FROM eval.coding_eval_queries_mimic4
WHERE length(note_text) <= ${MAX_Q_LEN}
ORDER BY random()
LIMIT ${N};
SQL
    fi
  fi

  eval_ids="$(psql -d "${DB}" -At -c "${SQL_QUERY}" || true)"
fi

if [[ -z "${eval_ids}" ]]; then
  echo "No eval_ids found (check filters / ICD10_ONLY / MAX_Q_LEN / USE_NOTE_GOLD)."
  exit 0
fi

# ---------------------------------------------------------------------------
# 2) Loop over eval_ids, call /coding_stream, save SSE
# ---------------------------------------------------------------------------

count=0

for eval_id in ${eval_ids}; do
  # Fetch raw note text for this eval (MIMIC note used as q)
  q="$(psql -d "${DB}" -At -c "
    SELECT note_text
    FROM eval.coding_eval_queries_mimic4
    WHERE eval_id = ${eval_id};
  ")"
  q_len=${#q}

  echo
  echo "=== eval_id=${eval_id} (len=${q_len}) ==="

  # Skip if note is still too long
  if [ "${q_len}" -gt "${MAX_Q_LEN}" ]; then
    echo "  -> skipped (len=${q_len} > MAX_Q_LEN=${MAX_Q_LEN})"
    continue
  fi

  out_file="${OUTDIR}/eval_${eval_id}.sse"

  # Assemble curl args
  curl_args=(
    -sS -N
    "${API_BASE}/api/rag/coding_stream"
    --get
    --data-urlencode "q=${q}"
    --data-urlencode "sources=icd10cm,snomed,icd11,loinc,rxnorm,mimic4_note"
    --data-urlencode "limit=8"
    --data-urlencode "ctx_k=128"
    --data-urlencode "with_llm=1"
    --data-urlencode "coding_mode=1"
  )

  if [[ "${USE_VALYU}" = "1" ]]; then
    curl_args+=(
      --data-urlencode "use_valyu=1"
      --data-urlencode "valyu_mode=answer"
      --data-urlencode "valyu_k=4"
      --data-urlencode "valyu_raw=0"
    )
  else
    curl_args+=( --data-urlencode "use_valyu=0" )
  fi

  # Run curl and write to file
  if curl "${curl_args[@]}" > "${out_file}"; then
    echo "  -> wrote ${out_file}"
  else
    echo "  !! curl failed for eval_id=${eval_id}"
  fi

  count=$((count + 1))
done

echo
echo "Completed ${count} eval call(s)."