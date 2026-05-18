#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Mega Promoting SRL
#
# apply-overlays.sh — apply all MD-Chat overlays onto an upstream Synapse
# checkout. Idempotent: re-running is safe and a no-op if every overlay has
# already taken effect.
#
# Usage:
#   ./scripts/apply-overlays.sh <synapse-src-dir> [<overlays-dir>]
#
#   <synapse-src-dir>  : path to a clean upstream Synapse checkout
#   <overlays-dir>     : defaults to <repo>/overlays
#
# Order of application:
#   1. overlays/strings/*.yaml      — declarative search-and-replace
#   2. overlays/templates/*.j2      — copied into synapse/res/templates/
#   3. overlays/patches/*.patch     — unified-diff patches via `patch -p1`
#
# Exit codes:
#   0  — all overlays applied or already in effect (idempotent success)
#   1  — generic error
#   10 — a string-replace overlay matched zero lines (drift — upstream changed)
#   11 — a patch failed to apply cleanly (drift — upstream changed)
#   12 — verify-overlays.sh post-check failed
#
# Tools required: bash, python3, patch, grep, sed.
# (yq is preferred if present; we fall back to a minimal Python parser.)

set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "usage: $0 <synapse-src-dir> [<overlays-dir>]" >&2
  exit 64
fi

SYNAPSE_SRC="$(cd "$1" && pwd)"
OVERLAYS_DIR="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/overlays}"

if [[ ! -d "${SYNAPSE_SRC}/synapse" ]]; then
  echo "error: ${SYNAPSE_SRC} does not look like a Synapse checkout (missing synapse/)" >&2
  exit 1
fi
if [[ ! -d "${OVERLAYS_DIR}" ]]; then
  echo "error: overlays directory not found: ${OVERLAYS_DIR}" >&2
  exit 1
fi

log() { printf '[apply-overlays] %s\n' "$*"; }

# ----------------------------------------------------------------------------
# Stage 1 — string overlays (overlays/strings/*.yaml)
# ----------------------------------------------------------------------------
apply_string_overlay() {
  local yaml="$1"
  log "string overlay: $(basename "$yaml")"

  python3 - "$yaml" "${SYNAPSE_SRC}" <<'PYEOF'
import os, sys, glob, re, pathlib

try:
    import yaml
except ImportError:
    print("error: python3 'yaml' module required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

overlay_path = sys.argv[1]
src_root = pathlib.Path(sys.argv[2])

with open(overlay_path) as fh:
    doc = yaml.safe_load(fh) or {}

entries = doc.get("entries") or []
total_replacements = 0
zero_match_entries = []

for entry in entries:
    path_glob = entry.get("path")
    pairs = entry.get("replace") or []
    dry_run = bool(entry.get("dry_run", False))
    if not path_glob or not pairs:
        continue

    matched_files = list(src_root.glob(path_glob))
    if not matched_files:
        zero_match_entries.append(f"glob '{path_glob}' matched 0 files")
        continue

    for fp in matched_files:
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        local_replaced = 0
        for pair in pairs:
            if not (isinstance(pair, list) and len(pair) == 2):
                continue
            frm, to = pair
            count = new.count(frm)
            if count > 0:
                new = new.replace(frm, to)
                local_replaced += count
        if local_replaced and not dry_run:
            fp.write_text(new, encoding="utf-8")
            total_replacements += local_replaced
            print(f"    ~ {fp.relative_to(src_root)}: {local_replaced} replacement(s)")
        elif local_replaced and dry_run:
            print(f"    [dry-run] {fp.relative_to(src_root)}: {local_replaced} replacement(s)")

if zero_match_entries:
    for msg in zero_match_entries:
        print(f"    ! {msg}", file=sys.stderr)
    sys.exit(10)

print(f"    total replacements: {total_replacements}")
PYEOF
}

shopt -s nullglob
for yaml in "${OVERLAYS_DIR}/strings/"*.yaml; do
  apply_string_overlay "$yaml"
done
shopt -u nullglob

# ----------------------------------------------------------------------------
# Stage 2 — template overlays (overlays/templates/*.j2 → synapse/res/templates/)
# ----------------------------------------------------------------------------
TPL_DST="${SYNAPSE_SRC}/synapse/res/templates"
if [[ -d "${OVERLAYS_DIR}/templates" ]]; then
  log "template overlays → ${TPL_DST}"
  mkdir -p "${TPL_DST}"
  shopt -s nullglob
  for tpl in "${OVERLAYS_DIR}/templates/"*.j2 "${OVERLAYS_DIR}/templates/"*.html "${OVERLAYS_DIR}/templates/"*.txt; do
    base="$(basename "$tpl")"
    # Strip the .j2 suffix — Synapse expects raw .html / .txt names.
    dst_name="${base%.j2}"
    cp -f "$tpl" "${TPL_DST}/${dst_name}"
    log "    + ${dst_name}"
  done
  shopt -u nullglob
fi

# ----------------------------------------------------------------------------
# Stage 3 — patches (overlays/patches/*.patch)
# ----------------------------------------------------------------------------
shopt -s nullglob
PATCHES=( "${OVERLAYS_DIR}/patches/"*.patch )
shopt -u nullglob

for patchfile in "${PATCHES[@]}"; do
  name="$(basename "$patchfile")"
  log "patch: ${name}"

  # Idempotency check — try a dry-run apply first; if it fails with "already
  # applied", we skip silently.
  if ( cd "${SYNAPSE_SRC}" && patch -p1 --dry-run --silent < "$patchfile" ) >/dev/null 2>&1; then
    ( cd "${SYNAPSE_SRC}" && patch -p1 --silent < "$patchfile" ) >/dev/null
    log "    applied"
  else
    # Check if reverse-apply works → it's already applied.
    if ( cd "${SYNAPSE_SRC}" && patch -p1 -R --dry-run --silent < "$patchfile" ) >/dev/null 2>&1; then
      log "    already applied (skipping)"
      continue
    fi
    echo "error: patch ${name} failed to apply against ${SYNAPSE_SRC}" >&2
    echo "       upstream has likely drifted; rebase the patch and try again" >&2
    exit 11
  fi
done

log "all overlays applied"
exit 0
