#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_clean_user_core_validation.sh [VALIDATION_ROOT]

Run the deterministic clean-user validation path against a fresh local vault.

Arguments:
  VALIDATION_ROOT  Optional target root for the temporary validation vault.
                   Default: /tmp/ctxvault-clean-verify
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VALIDATION_ROOT="${1:-/tmp/ctxvault-clean-verify}"
PYTHONPATH_VALUE="$REPO_ROOT/src"

echo "CtxVault clean-user deterministic validation"
echo "Repo root: $REPO_ROOT"
echo "Validation root: $VALIDATION_ROOT"

rm -rf "$VALIDATION_ROOT"
mkdir -p "$VALIDATION_ROOT/exports" "$VALIDATION_ROOT/artifacts"

python3 "$REPO_ROOT/scripts/run_deterministic_checks.py"

PYTHONPATH="$PYTHONPATH_VALUE" python3 -m ctxvault.cli init-vault --root "$VALIDATION_ROOT"
PYTHONPATH="$PYTHONPATH_VALUE" python3 -m ctxvault.cli seed-fixtures --root "$VALIDATION_ROOT"
PYTHONPATH="$PYTHONPATH_VALUE" python3 -m ctxvault.cli build-context \
  --root "$VALIDATION_ROOT" \
  --task-label "clean user validation" \
  --prompt-id prompt_schema_designer_v1 \
  --memory-query "local LLM"
PYTHONPATH="$PYTHONPATH_VALUE" python3 -m ctxvault.cli emit-agents-projection \
  --root "$VALIDATION_ROOT" \
  --workstream-id ws_20260421_ctxvault_schema \
  --output-path "$VALIDATION_ROOT/exports/AGENTS.md" \
  --receipt-output-path "$VALIDATION_ROOT/artifacts/agents-md-receipt.json"

test -f "$VALIDATION_ROOT/exports/AGENTS.md"
test -f "$VALIDATION_ROOT/artifacts/agents-md-receipt.json"

echo
echo "clean-user-validation: ok"
echo "AGENTS.md: $VALIDATION_ROOT/exports/AGENTS.md"
echo "ProjectionReceipt: $VALIDATION_ROOT/artifacts/agents-md-receipt.json"
