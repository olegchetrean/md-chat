#!/usr/bin/env bash
# Check for new upstream Element X Android tags. Weekly cron-friendly.

set -euo pipefail

UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/element-hq/element-x-android.git}"
PINNED_TAG="${UPSTREAM_TAG:-v26.05.1}"

latest=$(git ls-remote --tags --refs "$UPSTREAM_REPO" \
    | awk -F/ '{print $NF}' \
    | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
    | sort -V \
    | tail -1)

echo "MD-Chat Android upstream check"
echo "  currently pinned: $PINNED_TAG"
echo "  latest upstream:  $latest"

if [ "$latest" != "$PINNED_TAG" ]; then
    echo ""
    echo "ACTION: rebase needed. Set UPSTREAM_TAG=$latest and re-run fork-bootstrap.sh."
    exit 2
fi
echo "  up to date."
