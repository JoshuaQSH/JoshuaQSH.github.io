#!/usr/bin/env bash
set -euo pipefail

site_dir="${1:-public}"

if [[ ! -d "$site_dir" ]]; then
  echo "Site directory '$site_dir' not found. Build with Hugo first." >&2
  exit 1
fi

tmp_links="$(mktemp)"
tmp_missing="$(mktemp)"
trap 'rm -f "$tmp_links" "$tmp_missing"' EXIT

while IFS= read -r -d '' html_file; do
  perl -ne 'while(/(?:href|src)=\"([^\"]+)\"/g){print "$1\n"}' "$html_file" >> "$tmp_links" || true
done < <(find "$site_dir" -name "*.html" -print0)

sort -u "$tmp_links" | while IFS= read -r link; do
  case "$link" in
    http://*|https://*|mailto:*|javascript:*|tel:*|data:*|\#*|"")
      continue
      ;;
  esac

  clean="${link%%\#*}"
  clean="${clean%%\?*}"
  clean="${clean//&amp;/&}"
  if [[ "$clean" == "/livereload.js" ]]; then
    continue
  fi
  if [[ "$clean" == /* ]]; then
    target="${site_dir}${clean}"
  else
    target="${site_dir}/${clean}"
  fi

  if [[ -d "$target" ]]; then
    [[ -f "${target}/index.html" ]] || echo "${link} -> missing index in ${target}" >> "$tmp_missing"
  elif [[ -f "$target" || -f "${target}.html" || -f "${target}/index.html" ]]; then
    :
  else
    echo "${link} -> missing (${target})" >> "$tmp_missing"
  fi
done

if [[ -s "$tmp_missing" ]]; then
  echo "Internal link check failed:"
  cat "$tmp_missing"
  exit 1
fi

echo "Internal link check passed."
