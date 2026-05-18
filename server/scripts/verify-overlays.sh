#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Mega Promoting SRL
#
# verify-overlays.sh — post-apply sanity check. Confirms that:
#   1. No user-facing "Element" / "Riot" / "Vector" strings survive in the
#      template tree.
#   2. Every template referenced by the overlay set actually exists at the
#      destination path.
#   3. Every patch is in an "already-applied" state (reverse-apply succeeds).
#   4. Brand strings from overlays/strings/branding.yaml exist in the tree.
#
# Usage:
#   ./scripts/verify-overlays.sh <synapse-src-dir> [<overlays-dir>]
#
# Exit codes:
#   0  — verification passed
#   12 — verification failed (one or more checks)

set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "usage: $0 <synapse-src-dir> [<overlays-dir>]" >&2
  exit 64
fi

SYNAPSE_SRC="$(cd "$1" && pwd)"
OVERLAYS_DIR="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/overlays}"

failures=0
log()  { printf '[verify-overlays] %s\n' "$*"; }
fail() { printf '[verify-overlays] FAIL: %s\n' "$*" >&2; failures=$((failures+1)); }

# ----------------------------------------------------------------------------
# Check 1 — banned user-facing brand strings in templates and static assets
# ----------------------------------------------------------------------------
log "check 1/4 — banned strings in user-facing surfaces"
SCAN_PATHS=(
  "${SYNAPSE_SRC}/synapse/res/templates"
  "${SYNAPSE_SRC}/synapse/static"
)
PATTERN='(\bRiot\b|\bVector\b|\bElement\b|element\.io|riot\.im)'
hits=0
for p in "${SCAN_PATHS[@]}"; do
  [[ -d "$p" ]] || continue
  # Excluded: the protocol name "Matrix" and Synapse class names.
  if grep -RInE --binary-files=without-match \
       --exclude='mail-Vector.css' --exclude='mail-Element.css' \
       "$PATTERN" "$p" 2>/dev/null; then
    hits=$((hits+1))
  fi
done
if (( hits > 0 )); then
  fail "found ${hits} surviving Element/Riot/Vector references"
else
  log "  ok — no banned strings in templates/ or static/"
fi

# ----------------------------------------------------------------------------
# Check 2 — every overlay template landed at synapse/res/templates/
# ----------------------------------------------------------------------------
log "check 2/4 — overlay templates present at destination"
shopt -s nullglob
for tpl in "${OVERLAYS_DIR}/templates/"*.j2 "${OVERLAYS_DIR}/templates/"*.html "${OVERLAYS_DIR}/templates/"*.txt; do
  base="$(basename "$tpl")"
  dst_name="${base%.j2}"
  if [[ ! -f "${SYNAPSE_SRC}/synapse/res/templates/${dst_name}" ]]; then
    fail "missing template at destination: ${dst_name}"
  fi
done
shopt -u nullglob

# ----------------------------------------------------------------------------
# Check 3 — every patch reverse-applies cleanly (= already applied)
# ----------------------------------------------------------------------------
log "check 3/4 — patches in applied state"
shopt -s nullglob
for patchfile in "${OVERLAYS_DIR}/patches/"*.patch; do
  name="$(basename "$patchfile")"
  if ! ( cd "${SYNAPSE_SRC}" && patch -p1 -R --dry-run --silent < "$patchfile" ) >/dev/null 2>&1; then
    fail "patch not applied: ${name}"
  fi
done
shopt -u nullglob

# ----------------------------------------------------------------------------
# Check 4 — required MD-Chat brand strings present somewhere in the tree
# ----------------------------------------------------------------------------
log "check 4/4 — MD-Chat brand strings present in source tree"
REQUIRED_STRINGS=(
  "MD-Chat"
  "msg.md-chat.eu"
  "support@md-chat.eu"
)
for s in "${REQUIRED_STRINGS[@]}"; do
  if ! grep -RIn --binary-files=without-match -q -F "$s" \
        "${SYNAPSE_SRC}/synapse/res/templates" \
        "${SYNAPSE_SRC}/synapse/static" 2>/dev/null; then
    # Some strings live only in patched .py files — widen search.
    if ! grep -RIn --binary-files=without-match -q -F "$s" \
          "${SYNAPSE_SRC}/synapse" 2>/dev/null; then
      fail "required brand string missing from tree: ${s}"
    fi
  fi
done

# ----------------------------------------------------------------------------
if (( failures > 0 )); then
  echo "[verify-overlays] ${failures} check(s) failed" >&2
  exit 12
fi
log "all checks passed"
exit 0
