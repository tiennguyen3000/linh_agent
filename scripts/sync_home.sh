#!/usr/bin/env bash
# ============================================================================
# Linh home sync — one way, Hermes home -> Linh home.
# ============================================================================
# Linh's home is deliberately isolated from ~/.hermes (own sessions, memory, skills).
# Seeding copies the capability surface ONCE; after that the two homes drift apart.
# This script is the controlled way to pull later Hermes-side work into Linh.
#
# What it syncs: skills/  memories/  plugins/   (same set the seeder inherits)
#
# Safety rules baked in:
#   * DRY RUN by default — nothing is written unless --apply is passed.
#   * Never overwrite by default: only files missing on the Linh side are copied
#     (differences are still reported, so you can decide to re-run with --overwrite).
#   * skills/linh is never touched: it is the pinned Linh skill (ESSENTIAL_SKILLS).
#   * No deletions, ever. Files that exist only in Linh stay (--show-extra lists them).
#
# Usage:
#   bash scripts/sync_home.sh                      # dry run: show what would change
#   bash scripts/sync_home.sh --apply              # copy new files only
#   bash scripts/sync_home.sh --apply --overwrite  # also update changed files
#   bash scripts/sync_home.sh --only skills        # one area (skills|memories|plugins)
#   bash scripts/sync_home.sh --show-extra         # also list Linh-only files
#
# Env overrides: SRC_HOME (default ~/.hermes), DST_HOME (default $LINH_HOME or ~/.linh)
#
# Implementation note: every area is scanned with a DRY-RUN rsync first (that is what
# classifies NEW vs DIFF — testing the destination before anything is written), then a
# separate real pass copies. macOS ships openrsync ("rsync 2.6.9 compatible"), whose
# itemize codes do not mark new files with '+', so classification never relies on flags.
# ============================================================================
set -euo pipefail

SRC_HOME="${SRC_HOME:-$HOME/.hermes}"
DST_HOME="${DST_HOME:-${LINH_HOME:-$HOME/.linh}}"

APPLY=0
OVERWRITE=0
SHOW_EXTRA=0
AREAS="skills,memories,plugins"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --overwrite) OVERWRITE=1; shift ;;
    --show-extra) SHOW_EXTRA=1; shift ;;
    --only) AREAS="$2"; shift 2 ;;
    --src) SRC_HOME="$2"; shift 2 ;;
    --dst) DST_HOME="$2"; shift 2 ;;
    -h|--help) sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

die() { printf '\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

command -v rsync >/dev/null || die "rsync not found (macOS/Linux ship it; fall back to the manual cp in docs/INSTALL.md)"
[[ -d "$SRC_HOME" ]] || die "source home not found: $SRC_HOME"
[[ -d "$DST_HOME" ]] || die "Linh home not found: $DST_HOME — install/seed first (scripts/install.sh)"
[[ "$(cd "$SRC_HOME" && pwd -P)" != "$(cd "$DST_HOME" && pwd -P)" ]] || die "source and destination are the same home"

IFS=',' read -r -a AREA_LIST <<<"$AREAS"
for area in "${AREA_LIST[@]}"; do
  case "$area" in skills|memories|plugins) ;; *) die "invalid --only area: $area" ;; esac
done

BASE_EXCLUDES=(
  --exclude '.DS_Store'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  # Per-home bookkeeping, not capability: curator ledger, skill usage stats and the
  # bundled-skill manifest describe THIS home's history and must not be transplanted.
  --exclude '.curator_backups/'
  --exclude '.curator_ledger.jsonl'
  --exclude '.usage.json'
  --exclude '.bundled_manifest'
)

echo "Linh home sync  ($([[ $APPLY -eq 1 ]] && echo APPLY || echo DRY RUN))"
echo "  from: $SRC_HOME"
echo "  to:   $DST_HOME"
echo "  areas: ${AREA_LIST[*]}   overwrite: $([[ $OVERWRITE -eq 1 ]] && echo yes || echo no)"
echo

# scan <src-dir> <dst-dir> [extra-flags...] — DRY RUN; prints "new|diff <relpath>" per file.
scan() {
  local src="$1" dst="$2" out code name
  shift 2
  out="$(rsync -a --checksum --itemize-changes --out-format='%i %n%L' -n \
         "${BASE_EXCLUDES[@]}" "$@" "$src"/ "$dst"/ || true)"
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    code="${line%% *}"
    name="${line#* }"
    case "$code" in
      .*|'<'*) continue ;;                   # unchanged / destination-newer
    esac
    [[ "$name" == */ ]] && continue            # directory entry: files report individually
    [[ "$name" == *' -> '* ]] && name="${name%% -> *}"
    if [[ -e "$dst/$name" ]]; then echo "diff $name"; else echo "new $name"; fi
  done <<<"$out"
}

total_new=0
total_diff=0
total_extra=0

for area in "${AREA_LIST[@]}"; do
  src="$SRC_HOME/$area"
  dst="$DST_HOME/$area"
  if [[ ! -d "$src" ]]; then
    echo "== $area: skip (no source: $src)"
    continue
  fi
  mkdir -p "$dst"

  area_flags=()
  # The pinned Linh skill must never be replaced by a Hermes-side copy. Patterns are
  # relative to the transfer root, so for the skills area that is top-level `linh/`.
  [[ "$area" == "skills" ]] && area_flags+=(--exclude 'linh/')

  echo "== $area"
  new=0
  diff=0
  while read -r kind name; do
    if [[ "$kind" == "new" ]]; then
      printf '  NEW   %s\n' "$name"; new=$((new + 1))
    else
      printf '  DIFF  %s%s\n' "$name" \
        "$([[ $OVERWRITE -eq 0 ]] && echo '   (kept — pass --overwrite to update)' || echo '')"
      diff=$((diff + 1))
    fi
  done < <(scan "$src" "$dst" "${area_flags[@]+"${area_flags[@]}"}")
  [[ $new -eq 0 && $diff -eq 0 ]] && echo "  (up to date)"

  if [[ $APPLY -eq 1 && $((new + diff)) -gt 0 ]]; then
    copy_flags=()
    [[ $OVERWRITE -eq 0 ]] && copy_flags+=(--ignore-existing)
    rsync -a --checksum "${BASE_EXCLUDES[@]}" \
      "${area_flags[@]+"${area_flags[@]}"}" "${copy_flags[@]+"${copy_flags[@]}"}" \
      "$src"/ "$dst"/ >/dev/null
  fi

  if [[ $SHOW_EXTRA -eq 1 ]]; then
    while read -r kind name; do
      [[ "$kind" == "new" ]] || continue
      printf '  Linh-ONLY  %s (untouched)\n' "$name"; total_extra=$((total_extra + 1))
    done < <(scan "$dst" "$src" "${area_flags[@]+"${area_flags[@]}"}")
  fi

  total_new=$((total_new + new))
  total_diff=$((total_diff + diff))
done

echo
echo "Tổng: $total_new file mới, $total_diff file khác nội dung$([[ $SHOW_EXTRA -eq 1 ]] && echo ", $total_extra file chỉ có bên Linh")"
if [[ $APPLY -eq 0 ]]; then
  echo "DRY RUN — chưa ghi gì. Thêm --apply để copy ($([[ $OVERWRITE -eq 1 ]] && echo 'chế độ overwrite' || echo 'chỉ file mới'))."
else
  echo "Đã copy ($([[ $OVERWRITE -eq 1 ]] && echo 'overwrite' || echo 'chỉ file mới')). Không xoá gì, không đụng skills/linh."
  echo "Kiểm tra lại: linh selfcheck   (skill mới nhận ở phiên kế tiếp)"
fi
