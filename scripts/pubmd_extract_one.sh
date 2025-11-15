#!/usr/bin/env bash
set -euo pipefail
in="$1"
base="$(basename "$in" .xml.gz)"
out="$SPLIT_DIR/${base}.csv.gz"
stamp="$SPLIT_DIR/.ok/${base}.ok"

# already done?
[[ -f "$stamp" && -s "$out" ]] && exit 0

# stream-decompress → parser → compressed shard
# Change the Python entrypoint if yours lives elsewhere
gzip -cd "$in" \
 | python -m server.scripts.pubmd_xml_to_csv --stdin \
 | gzip > "$out".part

mv "$out".part "$out"
touch "$stamp"
