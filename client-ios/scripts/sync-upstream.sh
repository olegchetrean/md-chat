#!/usr/bin/env bash
# Detect new upstream Element X iOS releases. Cron-friendly: monthly.
# Prints a diff between the currently pinned tag and the latest upstream tag.

set -euo pipefail

UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/element-hq/element-x-ios.git}"
PINNED_TAG="${UPSTREAM_TAG:-26.05.13}"

latest=$(git ls-remote --tags --refs "$UPSTREAM_REPO" \
    | awk -F/ '{print $NF}' \
    | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' \
    | sort -V \
    | tail -1)

echo "MD-Chat iOS upstream check"
echo "  currently pinned: $PINNED_TAG"
echo "  latest upstream:  $latest"

if [ "$latest" != "$PINNED_TAG" ]; then
    echo ""
    echo "ACTION: rebase needed. Set UPSTREAM_TAG=$latest and re-run fork-bootstrap.sh,"
    echo "then verify overlay applies cleanly via apply-branding.sh --check."
    exit 2
fi

echo "  up to date."
