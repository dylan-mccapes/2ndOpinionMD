#!/usr/bin/env bash
# RTX-4090 / PortalNode: FORWARD 3-agent PTV harness with optional Stage E
# (MKG retrieval + overall synthesis grounded by the PTV summary).
#
# Pipeline per synthetic patient:
#   Stage A — eoh-llama (8B q8_0)              probe: PTV toolkit on patient graph
#   Stage B — eoh-llama (8B q8_0)              gap:   close what probe missed
#   Stage C — curation (Python)                merge probe + gap working sets
#   Stage D — eoh-llama (8B q8_0)              PTV synthesis -> patient timeline summary
#   Stage E — mkg_retrieval_harness.run_query  router + ANN + per-term FTS, then
#                                              eoh-llama overall synth that takes
#                                              both the rag_corpus hits AND the Stage-D
#                                              PTV summary as clinical_context.
#
# Outputs:
#   receipts/FORWARD_PTV_3AGENT_<UTC>.json
#   reports/FORWARD_PTV_3AGENT_<UTC>.pdf
#
# Prereqs (on the 4090 host):
#   - WSL Ubuntu venv with sentence-transformers + psycopg + requests + reportlab
#   - Ollama on host with all three models loaded:
#       ollama create eoh-llama        -f server/ollama/eoh-llama3.1-8b.Modelfile
#       ollama create eoh-llama3.2-source-router \
#           -f server/ollama/eoh-llama3.2-source-router.Modelfile
#   - SYNC_DATABASE_URL or DATABASE_URL pointing at the rag_corpus Postgres
#     (Stage E only — pass --no-mkg below to skip if the DB is unreachable)
#
# Env knobs (all optional):
#   OLLAMA_URL                 default http://127.0.0.1:11434 (set host IP from WSL)
#   FORWARD_PROBE_MODEL        default eoh-llama
#   FORWARD_GAP_MODEL          default eoh-llama
#   FORWARD_SYNTH_MODEL        default eoh-llama       (Stage D)
#   FORWARD_MKG_SYNTH_MODEL    default eoh-llama       (Stage E)
#   EOH_SOURCE_ROUTER_MODEL    default eoh-llama3.2-source-router
#   OLLAMA_SYNTH_NUM_CTX       default 16384
#   OLLAMA_ROUTER_NUM_CTX      default 8192
#   FORWARD_DISABLE_MKG=1      skip Stage E entirely (adds --no-mkg)
#   FORWARD_MKG_RESTRICT_SOURCES=1
#                              add --mkg-router-restrict-sources
#
# Examples:
#   scripts/portalnode4090_forward_ptv_3agent.sh
#   scripts/portalnode4090_forward_ptv_3agent.sh --patient-codes P1,P3
#   FORWARD_DISABLE_MKG=1 scripts/portalnode4090_forward_ptv_3agent.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"

export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export FORWARD_PROBE_MODEL="${FORWARD_PROBE_MODEL:-eoh-llama}"
export FORWARD_GAP_MODEL="${FORWARD_GAP_MODEL:-eoh-llama}"
export FORWARD_SYNTH_MODEL="${FORWARD_SYNTH_MODEL:-eoh-llama}"
export FORWARD_MKG_SYNTH_MODEL="${FORWARD_MKG_SYNTH_MODEL:-eoh-llama}"
export EOH_SOURCE_ROUTER_MODEL="${EOH_SOURCE_ROUTER_MODEL:-eoh-llama3.2-source-router}"
export OLLAMA_SYNTH_NUM_CTX="${OLLAMA_SYNTH_NUM_CTX:-16384}"
export OLLAMA_ROUTER_NUM_CTX="${OLLAMA_ROUTER_NUM_CTX:-8192}"

DISABLE_MKG="${FORWARD_DISABLE_MKG:-0}"
RESTRICT_MKG_SOURCES="${FORWARD_MKG_RESTRICT_SOURCES:-0}"

if [[ -f "$ROOT/.venv_embed/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.venv_embed/bin/activate"
elif [[ -f "$ROOT/.BeatingHeart/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.BeatingHeart/bin/activate"
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

EXTRA_ARGS=()
if [[ "$DISABLE_MKG" != "0" ]]; then
  EXTRA_ARGS+=("--no-mkg")
fi
if [[ "$RESTRICT_MKG_SOURCES" != "0" ]]; then
  EXTRA_ARGS+=("--mkg-router-restrict-sources")
fi

exec python server/scripts/forward_ptv_3agent_harness.py "${EXTRA_ARGS[@]}" "$@"
