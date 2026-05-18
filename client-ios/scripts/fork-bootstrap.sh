#!/usr/bin/env bash
# Bootstrap the MD-Chat iOS fork by cloning upstream Element X iOS at the pinned
# release tag and applying our overlay (branding, compliance modules, config
# defaults). Idempotent — safe to re-run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/element-hq/element-x-ios.git}"
UPSTREAM_TAG="${UPSTREAM_TAG:-26.05.13}"
WORKTREE="${WORKTREE:-$CLIENT_DIR/upstream}"

echo "MD-Chat iOS fork bootstrap"
echo "  upstream: $UPSTREAM_REPO"
echo "  tag:      $UPSTREAM_TAG"
echo "  worktree: $WORKTREE"

if [ ! -d "$WORKTREE/.git" ]; then
    echo "  cloning upstream (this can take a while)..."
    git clone --depth 1 --branch "$UPSTREAM_TAG" "$UPSTREAM_REPO" "$WORKTREE"
else
    echo "  upstream already cloned — fetching tag $UPSTREAM_TAG"
    (cd "$WORKTREE" && git fetch --depth 1 origin "tag:$UPSTREAM_TAG" "$UPSTREAM_TAG" && git checkout "$UPSTREAM_TAG")
fi

"$SCRIPT_DIR/apply-branding.sh" --worktree "$WORKTREE"

cd "$WORKTREE"
if command -v xcodegen >/dev/null 2>&1; then
    echo "  running xcodegen..."
    xcodegen generate
else
    echo "  WARNING: xcodegen not installed. brew install xcodegen, then rerun."
fi

echo "Fork bootstrap complete."
echo "Next: open the .xcodeproj in Xcode and build."
