#!/usr/bin/env bash
# Linh verify — end-to-end proof that this installation actually works.
#
# Everything here is a real check with a real exit code; nothing is asserted from
# documentation. Run after any change to the Linh layer:
#
#   bash scripts/verify.sh              # fast checks + affected tests
#   bash scripts/verify.sh --with-chat  # also spends one model call (identity smoke test)
#   bash scripts/verify.sh --full-agent-tests   # also runs the whole tests/agent tree
set -uo pipefail

LINH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$LINH_ROOT/venv/bin/python3"
export LINH_HOME="${LINH_HOME:-$HOME/.linh}"
export HERMES_HOME="$LINH_HOME"
FAILED=0

step() { printf '\n\033[1;36m== %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; FAILED=1; }

run_check() {  # run_check "<label>" <command...>
  local label="$1"; shift
  if "$@" >/tmp/linh_verify_step.log 2>&1; then ok "$label"; else
    bad "$label"; tail -15 /tmp/linh_verify_step.log | sed 's/^/      /'
  fi
}

step "1. Linh CLI"
run_check "linh version"  "$LINH_ROOT/bin/linh" version
run_check "linh identity" "$LINH_ROOT/bin/linh" identity
run_check "linh agents (6 roles)" "$LINH_ROOT/bin/linh" agents

step "2. Installation selfcheck"
run_check "linh selfcheck" "$LINH_ROOT/bin/linh" selfcheck

step "3. Rebrand layer is complete and idempotent"
if out="$("$PY" "$LINH_ROOT/scripts/rebrand_core.py" 2>&1)"; then
  if grep -q "0 edits across 0 files" <<<"$out"; then
    ok "no pending rebrand edits"
  else
    bad "rebrand had pending edits — re-run and commit"
    printf '%s\n' "$out" | sed 's/^/      /'
  fi
else
  bad "rebrand_core.py failed"
  printf '%s\n' "$out" | sed 's/^/      /'
fi

step "4. Isolation (Linh must not touch the Hermes home)"
if [[ "$(cd "$LINH_ROOT" && "$PY" -c 'from hermes_constants import get_hermes_home; print(get_hermes_home())')" == "$LINH_HOME" ]]
then ok "core resolves home to $LINH_HOME"
else bad "core resolved the wrong home (LINH_HOME override not in effect)"; fi
if [[ -f "$LINH_HOME/state.db" ]]; then ok "Linh state.db present (sessions are Linh-local)"
else echo "  · state.db not created yet (first run will create it)"; fi

step "5. Tests on the identity-affected files"
AFFECTED="tests/hermes_cli/test_banner.py tests/hermes_cli/test_skin_engine.py tests/hermes_cli/test_startup_fast_guards.py tests/hermes_cli/test_config.py tests/test_cli_skin_integration.py tests/agent/test_prompt_builder.py tests/agent/test_system_prompt.py tests/cli/test_exit_summary_resume_hint.py tests/hermes_state/test_resolve_resume_session_id.py"
# A fresh install (setup_venv.py --mode fresh) has runtime deps only; the suite needs
# the [dev] extra. Skip rather than fail — every other check still runs.
if "$PY" -c 'import pytest' >/dev/null 2>&1; then
  run_check "affected test files" env HERMES_PYTHON="$PY" bash -c \
    "cd '$LINH_ROOT/core' && scripts/run_tests.sh $AFFECTED"
else
  echo "  · skipped (pytest not installed) — install it with:"
  echo "      python3 scripts/setup_venv.py --mode fresh --with-dev"
fi

if [[ "${1:-}" == "--full-agent-tests" ]]; then
  step "6. Prompt/agent subsystem (tests/agent, full)"
  if "$PY" -c 'import pytest' >/dev/null 2>&1; then
    run_check "tests/agent/" env HERMES_PYTHON="$PY" bash -c \
      "cd '$LINH_ROOT/core' && scripts/run_tests.sh tests/agent/"
  else
    echo "  · skipped (pytest not installed)"
  fi
fi

if [[ "${1:-}" == "--with-chat" ]]; then
  step "7. Identity smoke test (one real model call)"
  if out="$("$LINH_ROOT/bin/linh" chat -q "Trả lời 1 câu: bạn là ai, ai sở hữu bạn?" 2>&1)"; then
    if grep -qi "Linh" <<<"$out"; then ok "agent identified itself as Linh"
    else bad "agent response did not mention Linh"; echo "$out" | tail -10 | sed 's/^/      /'; fi
  else bad "chat smoke test failed"; echo "$out" | tail -15 | sed 's/^/      /'; fi
fi

printf '\n'
if [[ $FAILED -eq 0 ]]; then printf '\033[1;32mLinh VERIFY: ALL GOOD\033[0m\n'; else
  printf '\033[1;31mLinh VERIFY: FAILURES ABOVE\033[0m\n'; fi
exit $FAILED
