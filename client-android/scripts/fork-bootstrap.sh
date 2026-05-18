#!/usr/bin/env bash
# Bootstrap the MD-Chat Android fork: clone upstream at pinned tag + apply
# overlay. Idempotent. Re-run after `sync-upstream.sh` detects a new tag.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/element-hq/element-x-android.git}"
UPSTREAM_TAG="${UPSTREAM_TAG:-v26.05.1}"
WORKTREE="${WORKTREE:-$CLIENT_DIR/upstream}"

echo "MD-Chat Android fork bootstrap"
echo "  upstream: $UPSTREAM_REPO"
echo "  tag:      $UPSTREAM_TAG"
echo "  worktree: $WORKTREE"

if [ ! -d "$WORKTREE/.git" ]; then
    echo "  cloning upstream..."
    git clone --depth 1 --branch "$UPSTREAM_TAG" "$UPSTREAM_REPO" "$WORKTREE"
else
    echo "  upstream already cloned; checking out tag"
    (cd "$WORKTREE" && git fetch --depth 1 origin "tag:$UPSTREAM_TAG" "$UPSTREAM_TAG" && git checkout "$UPSTREAM_TAG")
fi

"$SCRIPT_DIR/apply-branding.sh" --worktree "$WORKTREE"

cd "$WORKTREE"
echo "  running ./gradlew tasks (smoke check)..."
./gradlew --quiet tasks --all >/dev/null 2>&1 || {
    echo "  WARNING: gradle tasks failed. JDK 17+ required."
}

echo "Fork bootstrap complete."
echo "Build commands:"
echo "  ./gradlew assembleGplayDebug"
echo "  ./gradlew assembleFdroidDebug"
