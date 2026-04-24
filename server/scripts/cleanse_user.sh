#!/usr/bin/env bash
# cleanse_user.sh — wipe all user data except the PTV graph row
#
# Clears for a given email:
#   • ehr.patient_artifacts   (uploaded docs + raw bytes)
#   • ehr.patient_timeline    (ingested timeline events)
#   • public.sessions         (active vault sessions)
#   • public.patient_timelines (timeline metadata row)
#
# Preserves:
#   • ehr.patient_graph_vision  (PTV graph — kept so the user isn't fully blind)
#   • public.operators          (identity anchor)
#   • public.users              (account)
#
# Usage:
#   ./server/scripts/cleanse_user.sh dylan@2ndopinionmd.ai
#   ./server/scripts/cleanse_user.sh dylan@2ndopinionmd.ai --dry-run

set -euo pipefail

EMAIL="${1:-}"
DRY_RUN=false
if [[ "${2:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

if [[ -z "$EMAIL" ]]; then
    echo "Usage: $0 <email> [--dry-run]"
    exit 1
fi

# ---------------------------------------------------------------------------
# Resolve DB connection — prefer POSTGRES_DSN, fall back to DATABASE_URL
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

for env_file in "$PROJECT_ROOT/.env" "$PROJECT_ROOT/server/.env" "$PROJECT_ROOT/.pulse"; do
    if [[ -f "$env_file" ]]; then
        set -a; source "$env_file"; set +a
        break
    fi
done

DSN="${POSTGRES_DSN:-${DATABASE_URL:-}}"
if [[ -z "$DSN" ]]; then
    echo "ERROR: set POSTGRES_DSN or DATABASE_URL in your .env"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  cleanse_user.sh"
echo "  email:   $EMAIL"
echo "  dry-run: $DRY_RUN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

psql_exec() {
    psql "$DSN" -v ON_ERROR_STOP=1 -c "$1"
}

# ---------------------------------------------------------------------------
# Preview — always show counts before touching anything
# ---------------------------------------------------------------------------
echo ""
echo "📊 Current row counts for $EMAIL:"
psql "$DSN" <<SQL
SELECT
    u.email,
    u.id                                         AS user_id,
    o.operator_id,
    (SELECT COUNT(*) FROM public.sessions s
       WHERE s.operator_id = o.operator_id)      AS sessions,
    (SELECT COUNT(*) FROM public.patient_timelines pt
       WHERE pt.patient_operator_id = o.operator_id) AS timeline_meta_rows,
    (SELECT COUNT(*) FROM ehr.patient_timeline et
       WHERE et.patient_id = u.id::text)         AS timeline_events,
    (SELECT COUNT(*) FROM ehr.patient_artifacts pa
       WHERE pa.patient_id = u.id::text)         AS artifacts,
    (SELECT COUNT(*) FROM ehr.patient_graph_vision pgv
       WHERE pgv.patient_id = u.id::text)        AS ptv_graph_rows
FROM public.users u
LEFT JOIN public.operators o ON o.user_id = u.id
WHERE u.email = '$EMAIL';
SQL

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "🔍 Dry-run — no changes made."
    exit 0
fi

echo ""
read -rp "⚠️  Proceed with cleanse for $EMAIL? [y/N] " confirm
# Portable lowercase — ${var,,} requires Bash 4+ (macOS ships Bash 3.2).
_confirm_lc="$(printf '%s' "$confirm" | tr '[:upper:]' '[:lower:]')"
if [[ "$_confirm_lc" != "y" ]]; then
    echo "Aborted."
    exit 0
fi
unset _confirm_lc

# ---------------------------------------------------------------------------
# Execute cleanse (PTV graph row preserved)
# ---------------------------------------------------------------------------
echo ""
echo "🧹 Cleansing..."

psql "$DSN" -v ON_ERROR_STOP=1 <<SQL
DO \$\$
DECLARE
    v_user_id    UUID;
    v_operator_id UUID;
    v_patient_id  TEXT;
BEGIN
    SELECT id INTO v_user_id FROM public.users WHERE email = '$EMAIL';
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User not found: $EMAIL';
    END IF;

    v_patient_id := v_user_id::TEXT;

    SELECT operator_id INTO v_operator_id
    FROM public.operators WHERE user_id = v_user_id;

    -- 1. Timeline events
    DELETE FROM ehr.patient_timeline WHERE patient_id = v_patient_id;
    RAISE NOTICE 'Deleted ehr.patient_timeline rows for %', v_patient_id;

    -- 2. Uploaded artifacts (raw bytes + text)
    DELETE FROM ehr.patient_artifacts WHERE patient_id = v_patient_id;
    RAISE NOTICE 'Deleted ehr.patient_artifacts rows for %', v_patient_id;

    -- 3. Vault sessions
    IF v_operator_id IS NOT NULL THEN
        DELETE FROM public.sessions WHERE operator_id = v_operator_id;
        RAISE NOTICE 'Deleted sessions for operator %', v_operator_id;

        -- 4. Timeline metadata row
        DELETE FROM public.patient_timelines WHERE patient_operator_id = v_operator_id;
        RAISE NOTICE 'Deleted patient_timelines row for operator %', v_operator_id;
    END IF;

    -- ehr.patient_graph_vision is intentionally preserved.
    RAISE NOTICE 'PTV graph (ehr.patient_graph_vision) preserved.';
END;
\$\$;
SQL

echo ""
echo "✅ Done. PTV graph preserved. Account and operator identity intact."
echo ""
echo "📊 Row counts after cleanse:"
psql "$DSN" <<SQL
SELECT
    u.email,
    (SELECT COUNT(*) FROM public.sessions s
       JOIN public.operators o ON o.operator_id = s.operator_id
       WHERE o.user_id = u.id)                   AS sessions,
    (SELECT COUNT(*) FROM ehr.patient_timeline et
       WHERE et.patient_id = u.id::text)         AS timeline_events,
    (SELECT COUNT(*) FROM ehr.patient_artifacts pa
       WHERE pa.patient_id = u.id::text)         AS artifacts,
    (SELECT COUNT(*) FROM ehr.patient_graph_vision pgv
       WHERE pgv.patient_id = u.id::text)        AS ptv_graph_rows
FROM public.users u
WHERE u.email = '$EMAIL';
SQL
