#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

RESULTS_DIR="results/run_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RESULTS_DIR"

lean_available() {
  if ! command -v lean >/dev/null 2>&1; then
    return 1
  fi
  if [ -z "${PROOFBENCH_MINIF2F_LEAN_ROOT:-}" ]; then
    return 1
  fi

  root="$PROOFBENCH_MINIF2F_LEAN_ROOT"
  if [ ! -d "$root" ]; then
    return 1
  fi

  if [ -f "$root/src/minif2f_import.lean" ] || [ -f "$root/lean/src/minif2f_import.lean" ]; then
    return 0
  fi

  return 1
}

run_static_fallback() {
  echo "Running lightweight full-comparison in smoke mode (mock model + static verifier)."
  echo "Tip: set GEMINI_API_KEY and PROOFBENCH_MINIF2F_LEAN_ROOT to run Lean-grade full evaluation."

  PROOFBENCH_RESULTS_DIR="$RESULTS_DIR" uv --cache-dir .uv-cache run proofbench run <<EOF
llm_baseline,react
3
EOF
}

run_lean_full() {
  echo "Running Lean-grade full-comparison (Gemini + Lean verifier)."
  echo "Using Lean root from PROOFBENCH_MINIF2F_LEAN_ROOT: ${PROOFBENCH_MINIF2F_LEAN_ROOT}"

  uv --cache-dir .uv-cache run proofbench preflight

  PROOFBENCH_RESULTS_DIR="$RESULTS_DIR" uv --cache-dir .uv-cache run proofbench run <<EOF
llm_baseline,react
3
EOF
}

if lean_available; then
  if [ -n "${GEMINI_API_KEY:-}" ]; then
    run_lean_full
    exit 0
  fi
  echo "GEMINI_API_KEY is not set; falling back to mock/static mode."
fi

uv --cache-dir .uv-cache run proofbench preflight --skip-lean
run_static_fallback
