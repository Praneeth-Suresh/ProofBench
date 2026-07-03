#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/clean_runs.sh [RESULT_DIR ...] [--dry-run]

Delete benchmark run artifacts and logs from previous tests.

Each result directory may contain:
- run_*.jsonl (per-run records)
- dashboard*.html (generated dashboards)
- *.log (run-time logs)

By default this script cleans:
- $PROOFBENCH_RESULTS_DIR if set, otherwise ./results
- ./y

If directories are provided as arguments, those paths replace the defaults.
Use --dry-run to preview deletions without removing files.
EOF
}

dry_run=false
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

paths=()
for arg in "$@"; do
  if [[ "$arg" == "--dry-run" ]]; then
    dry_run=true
  else
    paths+=( "$arg" )
  fi
done

if [[ ${#paths[@]} -eq 0 ]]; then
  if [[ -n "${PROOFBENCH_RESULTS_DIR:-}" ]]; then
    paths+=( "${PROOFBENCH_RESULTS_DIR}" )
  else
    paths+=( "results" )
  fi
  paths+=( "y" )
fi

normalize_dir() {
  local dir="$1"
  if [[ "$dir" = ~* ]]; then
    dir="${dir/#\~/$HOME}"
  fi
  if [[ ! -d "$dir" ]]; then
    return 1
  fi
  printf '%s\n' "$dir"
}

files=()
for raw_dir in "${paths[@]}"; do
  if ! dir="$(normalize_dir "$raw_dir")"; then
    continue
  fi

  while IFS= read -r path; do
    files+=( "$path" )
  done < <(
    find "$dir" -maxdepth 2 -type f \( \
      -name 'run_*.jsonl' -o \
      -name 'dashboard*.html' -o \
      -name '*.log' \
    \)
  )
done

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No benchmark run files found."
  exit 0
fi

printf 'This will remove %d file(s):\n' "${#files[@]}"
for file in "${files[@]}"; do
  echo " - $file"
done

if [[ "$dry_run" == true ]]; then
  echo "Dry run enabled, no files deleted."
  exit 0
fi

read -r -p "Type 'yes' to confirm deletion: " confirm
if [[ "$confirm" != "yes" ]]; then
  echo "Aborted."
  exit 1
fi

for file in "${files[@]}"; do
  rm -f -- "$file"
done

echo "Deleted ${#files[@]} file(s)."
