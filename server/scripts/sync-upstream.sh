#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Mega Promoting SRL
#
# sync-upstream.sh — detect drift between our pinned Synapse version and the
# latest stable upstream release.
#
# Usage:
#   ./scripts/sync-upstream.sh                # human-readable report
#   ./scripts/sync-upstream.sh --json         # machine-readable, for CI
#   ./scripts/sync-upstream.sh --fail-on-drift  # exit 2 if a newer tag exists
#
# Exit codes:
#   0  — up to date OR drift detected (informational)
#   2  — drift detected AND --fail-on-drift was set
#   3  — could not reach upstream / parse Dockerfile
#
# Intended to be invoked by a weekly CI cron AND ad-hoc by humans.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKERFILE="${SERVER_DIR}/Dockerfile"
UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/element-hq/synapse.git}"

JSON_MODE=0
FAIL_ON_DRIFT=0
for arg in "$@"; do
  case "$arg" in
    --json)            JSON_MODE=1 ;;
    --fail-on-drift)   FAIL_ON_DRIFT=1 ;;
    --help|-h)
      sed -n '3,18p' "$0"
      exit 0
      ;;
    *) echo "unknown flag: $arg" >&2; exit 64 ;;
  esac
done

if [[ ! -f "${DOCKERFILE}" ]]; then
  echo "error: Dockerfile not found at ${DOCKERFILE}" >&2
  exit 3
fi

# Extract the pinned tag from the Dockerfile ARG default.
PINNED="$(grep -E '^ARG +SYNAPSE_VERSION=' "${DOCKERFILE}" | head -n1 | sed -E 's/.*=//')"
if [[ -z "${PINNED}" ]]; then
  echo "error: could not parse SYNAPSE_VERSION from ${DOCKERFILE}" >&2
  exit 3
fi

# Fetch the latest *stable* tag from upstream (excludes -rc, -dev, etc.).
if ! LATEST="$(git ls-remote --tags --refs "${UPSTREAM_REPO}" \
                | awk '{print $2}' \
                | sed 's#refs/tags/##' \
                | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
                | sort -V | tail -n1)"; then
  echo "error: failed to query ${UPSTREAM_REPO}" >&2
  exit 3
fi

if [[ -z "${LATEST}" ]]; then
  echo "error: no stable tags discovered upstream" >&2
  exit 3
fi

DRIFT="false"
if [[ "${PINNED}" != "${LATEST}" ]]; then
  DRIFT="true"
fi

if (( JSON_MODE )); then
  cat <<EOF
{"pinned":"${PINNED}","latest":"${LATEST}","drift":${DRIFT},"upstream":"${UPSTREAM_REPO}"}
EOF
else
  echo "MD-Chat Synapse upstream sync check"
  echo "  upstream repo : ${UPSTREAM_REPO}"
  echo "  pinned tag    : ${PINNED}"
  echo "  latest stable : ${LATEST}"
  if [[ "${DRIFT}" == "true" ]]; then
    echo "  status        : DRIFT — newer stable tag available"
    echo
    echo "Next step:"
    echo "  1. Read upstream release notes:"
    echo "     https://github.com/element-hq/synapse/releases/tag/${LATEST}"
    echo "  2. Bump SYNAPSE_VERSION in Dockerfile and rebuild."
    echo "  3. Run ./scripts/apply-overlays.sh on a fresh clone to detect overlay drift."
  else
    echo "  status        : up to date"
  fi
fi

if [[ "${DRIFT}" == "true" && "${FAIL_ON_DRIFT}" -eq 1 ]]; then
  exit 2
fi
exit 0
