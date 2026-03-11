#!/usr/bin/env bash
set -euo pipefail

missing=0

check_file() {
  local file="$1"
  if ! rg -q '^tags:\s*\[[^]]+\]\s*$' "$file"; then
    echo "Missing or empty inline tags in: $file"
    missing=1
  fi
}

for file in content/posts/*.md content/hodgepodge/*.md; do
  [[ "$(basename "$file")" == "_index.md" ]] && continue
  check_file "$file"
done

if [[ "$missing" -ne 0 ]]; then
  echo "Tag check failed. Every post must define non-empty inline tags."
  exit 1
fi

echo "Tag check passed."
