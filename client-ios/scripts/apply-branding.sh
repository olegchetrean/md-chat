#!/usr/bin/env bash
# Apply MD-Chat brand overlay onto an upstream Element X iOS worktree.
# Replaces strings + drops in our compliance modules + config defaults.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OVERLAY_DIR="$CLIENT_DIR/overlays"

WORKTREE=""
DRY_RUN=0
CHECK_ONLY=0

while [ $# -gt 0 ]; do
    case "$1" in
        --worktree) WORKTREE="$2"; shift 2 ;;
        --dry-run)  DRY_RUN=1; shift ;;
        --check)    CHECK_ONLY=1; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

WORKTREE="${WORKTREE:-$CLIENT_DIR/upstream}"

if [ ! -d "$WORKTREE" ]; then
    echo "ERROR: worktree not found: $WORKTREE"
    echo "Run fork-bootstrap.sh first."
    exit 1
fi

echo "Applying MD-Chat overlay onto $WORKTREE"

# Apply string replacements via Python helper (PyYAML on python3).
python3 - "$OVERLAY_DIR/branding.yaml" "$WORKTREE" "$DRY_RUN" <<'PYEOF'
import sys
import os
import re
import yaml

cfg_path, worktree, dry_run = sys.argv[1], sys.argv[2], sys.argv[3] == "1"

with open(cfg_path) as f:
    cfg = yaml.safe_load(f)

count = 0
for entry in cfg.get("replacements", []):
    pattern = entry["pattern"]
    replacement = entry["replacement"]
    paths = entry.get("paths", ["**/*.swift", "**/*.strings", "**/*.plist", "**/project.yml"])
    for root, _, files in os.walk(worktree):
        for name in files:
            full = os.path.join(root, name)
            relevant = any(name.endswith(p.lstrip("**/")) for p in paths)
            if not relevant:
                continue
            try:
                with open(full, "r", encoding="utf-8") as f:
                    src = f.read()
            except Exception:
                continue
            new = re.sub(pattern, replacement, src)
            if new != src:
                count += 1
                print(f"  patched: {os.path.relpath(full, worktree)}")
                if not dry_run:
                    with open(full, "w", encoding="utf-8") as f:
                        f.write(new)
print(f"Total files patched: {count}")
PYEOF

# Drop in compliance modules
mkdir -p "$WORKTREE/ElementX/Sources/Compliance"
cp -v "$OVERLAY_DIR/Compliance/"*.swift "$WORKTREE/ElementX/Sources/Compliance/" 2>/dev/null || true

# Drop in config defaults
mkdir -p "$WORKTREE/ElementX/Sources/Configuration"
cp -v "$OVERLAY_DIR/Config/HomeserverDefaults.swift" "$WORKTREE/ElementX/Sources/Configuration/" 2>/dev/null || true

# Drop in localization
cp -v "$OVERLAY_DIR/strings/Localizable-ro.strings" "$WORKTREE/ElementX/Resources/Localizations/ro.lproj/Localizable.strings" 2>/dev/null || true
cp -v "$OVERLAY_DIR/strings/Localizable-ru.strings" "$WORKTREE/ElementX/Resources/Localizations/ru.lproj/Localizable.strings" 2>/dev/null || true

# Drop in AppIcon
cp -v "$OVERLAY_DIR/assets/AppIcon.appiconset/Contents.json" "$WORKTREE/ElementX/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json" 2>/dev/null || true

touch "$WORKTREE/.overlay-applied"
echo "Overlay applied."
