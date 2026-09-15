#!/usr/bin/env bash
# Linh — core acquisition step.
#
# The Linh distribution is two things in one repo:
#   * the Linh layer  (branch `main`)  — CLI, identity, scripts, docs
#   * the runtime core (branch `core`) — forked Hermes core with the Linh identity layer
#
# This script materialises the runtime into <LINH_ROOT>/core, from whichever source
# is available:
#
#   --mode local  rsync from the local Hermes checkout (fast, same-machine rebuilds)
#   --mode git    clone the `core` branch of the Linh repo (fresh machine, no Hermes)
#   --mode auto   (default) local when ~/.hermes/hermes-agent exists, else git
#
# Re-runnable (idempotent). An existing core/ is updated in place, never deleted:
# a conflicting core/ is moved aside to core.bak-<timestamp> instead of being removed.
set -euo pipefail

SRC="${SRC:-$HOME/.hermes/hermes-agent}"
DST="${DST:-$HOME/Linh/core}"
MODE="${MODE:-auto}"
REF="${REF:-core}"
REPO="${REPO:-https://github.com/tiennguyen3000/linh_agent.git}"
UPSTREAM="${UPSTREAM:-https://github.com/NousResearch/hermes-agent}"

usage() {
  cat <<'EOF'
usage: clone_core.sh [--mode auto|local|git] [--repo URL] [--ref BRANCH] [--src DIR] [--dst DIR]

  --mode local   copy the core from a local Hermes checkout ($SRC)
  --mode git     clone the core branch from the Linh repo ($REPO)
  --mode auto    local if $SRC has a core tree, else git   (default)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --ref)  REF="$2"; shift 2 ;;
    --src)  SRC="$2"; shift 2 ;;
    --dst)  DST="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

has_core_tree() { [[ -d "$1/agent" && -d "$1/hermes_cli" && -d "$1/tools" ]]; }

case "$MODE" in
  local|git) ;;
  auto)
    if has_core_tree "$SRC"; then MODE=local; else MODE=git; fi
    echo "== source auto-detected: $MODE"
    ;;
  *) echo "invalid --mode: $MODE" >&2; exit 2 ;;
esac

if [[ "$MODE" == "local" && ! -d "$SRC" ]]; then
  echo "local core source not found: $SRC" >&2
  echo "either pass --src <dir> or use --mode git" >&2
  exit 1
fi

echo "== Linh core: mode=$MODE -> $DST"

if [[ "$MODE" == "local" ]]; then
  mkdir -p "$DST"
  rsync -a \
    --exclude node_modules \
    --exclude .git \
    --exclude venv \
    --exclude __pycache__ \
    --exclude '*.pyc' \
    --exclude .pytest_cache \
    --exclude .ruff_cache \
    --exclude .mypy_cache \
    --exclude '*.egg-info' \
    --exclude .web_ui_build.lock \
    --exclude .ds_store \
    "$SRC"/ "$DST"/
else
  if [[ -d "$DST/.git" ]] && ! has_core_tree "$DST"; then
    echo "== existing $DST is not a core tree — moving it aside"
    mv "$DST" "$DST.bak-$(date +%Y%m%d_%H%M%S)"
  fi
  if [[ -d "$DST/.git" ]]; then
    echo "== updating existing core checkout (fetch $REF)"
    git -C "$DST" fetch --depth 1 origin "$REF"
    git -C "$DST" checkout -B "$REF" FETCH_HEAD
  elif [[ -n "$(ls -A "$DST" 2>/dev/null || true)" ]]; then
    echo "== $DST is not empty and not a git checkout — moving it aside"
    mv "$DST" "$DST.bak-$(date +%Y%m%d_%H%M%S)"
    git clone --depth 1 --branch "$REF" --single-branch "$REPO" "$DST"
  else
    mkdir -p "$(dirname "$DST")"
    git clone --depth 1 --branch "$REF" --single-branch "$REPO" "$DST"
  fi
fi

# Keep the upstream link so merged fixes stay possible (`git fetch upstream main`).
if [[ -d "$DST/.git" ]]; then
  if ! git -C "$DST" remote get-url upstream >/dev/null 2>&1; then
    git -C "$DST" remote add upstream "$UPSTREAM" || true
  fi
  echo "== core revision: $(git -C "$DST" log -1 --format='%h %ci %s')"
fi

echo "== size:"
du -sh "$DST"
echo "== package check:"
cd "$DST" && ls -d agent tools hermes_cli gateway cron plugins >/dev/null && echo "key packages present"
