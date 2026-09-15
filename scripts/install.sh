#!/usr/bin/env bash
# ============================================================================
# Linh installer — fresh machine, from the Git repo.
# ============================================================================
# Installs the whole distribution: Linh layer (this repo) + runtime core (the
# repo's `core` branch) + Linh's own venv + ~/.linh home + the `linh` command.
#
# Quick start (private repo — authenticate first, see docs/INSTALL.md):
#   git clone https://github.com/tiennguyen3000/linh_agent.git ~/Linh
#   bash ~/Linh/scripts/install.sh
#
# Same-machine rebuild (Hermes install present, no download needed):
#   bash scripts/install.sh --from-hermes
#
# Flags:
#   --dir DIR         install location                (default ~/Linh)
#   --repo URL        Linh repo                       (default github tiennguyen3000/linh_agent)
#   --core-ref REF    core branch                     (default core)
#   --mode M          core source: auto|local|git     (default auto)
#   --from-hermes     take core + venv from ~/.hermes/hermes-agent (local rebuild)
#   --extras SPEC     fresh venv extras (default all) e.g. --extras messaging
#   --with-dev        fresh venv also installs [dev] (pytest …) for scripts/verify.sh
#   --venv-mode M     venv source: auto|clone|fresh  (default auto)
#   --no-link         don't symlink into ~/.local/bin
#   --force-seed      overwrite ~/.linh config/skills
#   --skip-verify     stop before scripts/verify.sh
#   --with-chat       verify also spends one model call
# ============================================================================
set -euo pipefail

REPO_URL="${LINH_REPO_URL:-https://github.com/tiennguyen3000/linh_agent.git}"
CORE_REF="${LINH_CORE_REF:-core}"
LINH_DIR="${LINH_DIR:-$HOME/Linh}"
BIN_DIR="${LINH_BIN_DIR:-$HOME/.local/bin}"
CORE_MODE="auto"
VENV_MODE="auto"
LINK=1
FORCE_SEED=0
SKIP_VERIFY=0
VERIFY_ARGS=()
SEED_ARGS=()
VENV_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) LINH_DIR="$2"; shift 2 ;;
    --repo) REPO_URL="$2"; shift 2 ;;
    --core-ref) CORE_REF="$2"; shift 2 ;;
    --mode) CORE_MODE="$2"; shift 2 ;;
    --from-hermes) CORE_MODE=local ;;
    --no-link) LINK=0; shift ;;
    --force-seed) SEED_ARGS+=(--force); shift ;;
    --venv-mode) VENV_MODE="$2"; shift 2 ;;
    --extras) VENV_ARGS+=(--extras "$2"); shift 2 ;;
    --with-dev) VENV_ARGS+=(--with-dev); shift ;;
    --skip-verify) SKIP_VERIFY=1; shift ;;
    --with-chat) VERIFY_ARGS+=(--with-chat); shift ;;
    -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

step() { printf '\n\033[1;36m── %s\033[0m\n' "$1"; }
die()  { printf '\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

export LINH_HOME="${LINH_HOME:-$HOME/.linh}"
export HERMES_HOME="$LINH_HOME"
unset PYTHONPATH PYTHONHOME || true

step "0/6 prerequisites"
command -v git >/dev/null || die "git is required"
BOOT_PY=""
for cand in python3.12 python3.11 python3.13 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
      BOOT_PY="$(command -v "$cand")"; break
    fi
  fi
done
[[ -n "$BOOT_PY" ]] || die "no python3 (>=3.8) on PATH"
echo "  git:    $(git --version)"
echo "  python: $BOOT_PY ($("$BOOT_PY" -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])'))"
echo "  target: $LINH_DIR    home: $LINH_HOME"

step "1/6 Linh layer in $LINH_DIR"
if [[ -d "$LINH_DIR/.git" ]]; then
  echo "  existing checkout: $(git -C "$LINH_DIR" log -1 --format='%h %s')"
elif [[ -n "$(ls -A "$LINH_DIR" 2>/dev/null || true)" ]]; then
  die "$LINH_DIR exists and is not a git checkout — move it aside or pass --dir"
else
  # --single-branch: a plain clone also pulls the multi-MB `core` branch pack, which
  # step 2 fetches anyway into core/. Skipping it halves the download.
  echo "  cloning $REPO_URL (branch ${LINH_LAYER_REF:-main}, single-branch)"
  mkdir -p "$(dirname "$LINH_DIR")"
  git clone --single-branch --branch "${LINH_LAYER_REF:-main}" "$REPO_URL" "$LINH_DIR"
fi
[[ -f "$LINH_DIR/scripts/install.sh" ]] || die "$LINH_DIR does not look like a Linh checkout"

step "2/6 runtime core (branch $CORE_REF)"
bash "$LINH_DIR/scripts/clone_core.sh" --mode "$CORE_MODE" --repo "$REPO_URL" \
  --ref "$CORE_REF" --dst "$LINH_DIR/core"

step "3/6 apply the Linh identity layer"
"$BOOT_PY" "$LINH_DIR/scripts/rebrand_core.py"

step "4/6 build Linh's own venv ($VENV_MODE)"
"$BOOT_PY" "$LINH_DIR/scripts/setup_venv.py" --mode "$VENV_MODE" "${VENV_ARGS[@]+"${VENV_ARGS[@]}"}"

step "5/6 seed the Linh home ($LINH_HOME)"
if [[ ${#SEED_ARGS[@]} -gt 0 ]]; then
  "$BOOT_PY" "$LINH_DIR/scripts/seed_home.py" "${SEED_ARGS[@]}"
else
  "$BOOT_PY" "$LINH_DIR/scripts/seed_home.py"
fi

if [[ $LINK -eq 1 ]]; then
  mkdir -p "$BIN_DIR"
  ln -sfn "$LINH_DIR/bin/linh" "$BIN_DIR/linh"
  echo "  linked: $BIN_DIR/linh -> $LINH_DIR/bin/linh"
  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "  NOTE: $BIN_DIR is not on PATH. Add to your shell rc:"
       echo "        export PATH=\"$BIN_DIR:\$PATH\"" ;;
  esac
fi

if [[ $SKIP_VERIFY -eq 1 ]]; then
  step "6/6 verify: skipped (--skip-verify)"
else
  step "6/6 verify"
  bash "$LINH_DIR/scripts/verify.sh" "${VERIFY_ARGS[@]+"${VERIFY_ARGS[@]}"}"
fi

printf '\n\033[1;32mLinh installed.\033[0m  Chat: linh    Delegate: linh team code "<task>"\n'
echo "First run on a fresh machine: add credentials with 'linh setup' (or edit $LINH_HOME/.env)."
