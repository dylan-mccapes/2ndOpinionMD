#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

log() { printf '[pubmed-baseline] %s\n' "$*" >&2; }
die() { printf '[pubmed-baseline:ERROR] %s\n' "$*" >&2; exit 1; }

# ------------------------------------------------------------------------------
# Config (env overrides supported)
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DEST_DIR="${PUBMED_BASELINE_DIR:-${REPO_ROOT}/data/pubmd/baseline}"
REMOTE_URL="${PUBMED_BASELINE_REMOTE:-https://ftp.ncbi.nlm.nih.gov/pubmed/baseline}"
# 25 = PubMed 2025 baseline. Change to 26 next year or export PUBMED_BASELINE_PREFIX=pubmed26n
PREFIX="${PUBMED_BASELINE_PREFIX:-pubmed25n}"
JOBS="${PUBMED_JOBS:-8}"

# ------------------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------------------
need() { command -v "$1" >/dev/null 2>&1 || die "Missing dependency: $1"; }

md5_hash() {
  # Prints md5 hash of file to stdout (no filename)
  if command -v md5 >/dev/null 2>&1; then
    md5 -q "$1"
  elif command -v md5sum >/dev/null 2>&1; then
    md5sum "$1" | awk '{print $1}'
  else
    die "No md5 or md5sum on PATH"
  fi
}

ensure_layout() {
  mkdir -p "${DEST_DIR}"
  cd "${DEST_DIR}"
  # working files live alongside the downloads to keep paths simple
  : > REMOTE_ALL.txt
  : > REMOTE_GZ.txt
  : > REMOTE_MD5.txt
  : > URLS_GZ.txt
  : > URLS_MD5.txt
}

refresh_manifests() {
  log "Refreshing remote manifests from ${REMOTE_URL}..."
  curl -fsSL "${REMOTE_URL}/" \
    | sed -nE 's/.*href="(pubmed[0-9]{2}n[0-9]{4}\.xml\.gz(\.md5)?)".*/\1/p' \
    | sort -u > REMOTE_ALL.txt

  # Split into .gz and .md5 lists, restricted to the selected year prefix
  grep -E "^${PREFIX}[0-9]{4}\.xml\.gz$"        REMOTE_ALL.txt > REMOTE_GZ.txt || true
  grep -E "^${PREFIX}[0-9]{4}\.xml\.gz\.md5$"   REMOTE_ALL.txt > REMOTE_MD5.txt || true

  awk -v R="${REMOTE_URL}/" '{print R $0}' REMOTE_GZ.txt  > URLS_GZ.txt
  awk -v R="${REMOTE_URL}/" '{print R $0}' REMOTE_MD5.txt > URLS_MD5.txt

  log "Found $(wc -l < REMOTE_GZ.txt | tr -d '[:space:]') .gz files for ${PREFIX}*"
}

download_all() {
  need aria2c
  ensure_layout
  refresh_manifests

  # Download .md5 sidecars first, then the .gz archives (both resumable)
  if [ -s URLS_MD5.txt ]; then
    log "Downloading/updating .md5 files with aria2c (jobs=${JOBS})..."
    aria2c --dir="${DEST_DIR}" --input-file=URLS_MD5.txt \
      --continue=true --max-concurrent-downloads="${JOBS}" \
      --auto-file-renaming=false --check-integrity=true \
      --console-log-level=warn
  fi

  if [ -s URLS_GZ.txt ]; then
    log "Downloading/updating .gz files with aria2c (jobs=${JOBS})..."
    aria2c --dir="${DEST_DIR}" --input-file=URLS_GZ.txt \
      --continue=true --max-concurrent-downloads="${JOBS}" \
      --auto-file-renaming=false --check-integrity=true \
      --console-log-level=warn
  fi

  log "Download stage complete."
}

verify_all() {
  ensure_layout
  shopt -s nullglob
  local failed=0
  for gz in ${PREFIX}[0-9][0-9][0-9][0-9].xml.gz; do
    local md5f="${gz}.md5"
    if [ ! -f "${md5f}" ]; then
      # Fetch missing sidecar on-the-fly
      log "Fetching missing sidecar: ${md5f}"
      curl -fsSLo "${md5f}" "${REMOTE_URL}/${gz}.md5" || {
        log "WARN: could not retrieve ${md5f}"; failed=1; continue;
      }
    fi
    local expected actual
    expected="$(awk '{print $1}' "${md5f}" | tr -d '\r\n')"
    actual="$(md5_hash "${gz}")"
    if [ -z "${expected}" ]; then
      log "WARN: empty expected MD5 for ${gz}"
      failed=1
      continue
    fi
    if [ "${expected}" = "${actual}" ]; then
      printf 'OK   %s\n' "${gz}"
    else
      printf 'FAIL %s (got %s expected %s)\n' "${gz}" "${actual}" "${expected}"
      failed=1
    fi
  done
  shopt -u nullglob
  if [ "${failed}" -ne 0 ]; then
    die "One or more files failed MD5 verification."
  fi
  log "All present files passed MD5 verification."
}

list_some() {
  ensure_layout
  printf '(pwd: %s)\n' "$(pwd)"
  shopt -s nullglob
  local count=0
  for _ in ${PREFIX}[0-9][0-9][0-9][0-9].xml.gz; do count=$((count+1)); done
  printf 'Local .gz count matching %s*: %d\n' "${PREFIX}" "${count}"
  if [ "${count}" -gt 0 ]; then
    printf 'Sample:\n'
    ls -1 ${PREFIX}[0-9][0-9][0-9][0-9].xml.gz | head -n 10
  fi
  shopt -u nullglob
}

usage() {
  cat <<EOF
Usage: $(basename "$0") <command>

Commands:
  sync     Download/update PubMed baseline (${PREFIX}*) with aria2c
  verify   MD5-verify all local ${PREFIX}*.xml.gz files
  list     Show working dir and a sample of files
  refresh  Refresh remote manifests only

Env overrides:
  PUBMED_BASELINE_DIR     (default: ${DEST_DIR})
  PUBMED_BASELINE_REMOTE  (default: ${REMOTE_URL})
  PUBMED_BASELINE_PREFIX  (default: ${PREFIX})
  PUBMED_JOBS             (default: ${JOBS})

Examples:
  PUBMED_JOBS=12 $(basename "$0") sync
  PUBMED_BASELINE_PREFIX=pubmed26n $(basename "$0") sync
EOF
}

main() {
  local cmd="${1:-help}"
  case "${cmd}" in
    sync)    download_all ;;
    verify)  verify_all ;;
    list)    list_some ;;
    refresh) ensure_layout; refresh_manifests; log "Manifests refreshed." ;;
    help|--help|-h) usage ;;
    *) die "Unknown command: ${cmd}";;
  esac
}

main "${@:-}"
