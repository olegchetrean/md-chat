#!/usr/bin/env bash
# Apply MD-Chat brand overlay onto an upstream Element X Android worktree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OVERLAY_DIR="$CLIENT_DIR/overlays"

WORKTREE=""
DRY_RUN=0

while [ $# -gt 0 ]; do
    case "$1" in
        --worktree) WORKTREE="$2"; shift 2 ;;
        --dry-run)  DRY_RUN=1; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

WORKTREE="${WORKTREE:-$CLIENT_DIR/upstream}"
if [ ! -d "$WORKTREE" ]; then
    echo "ERROR: worktree not found: $WORKTREE"; exit 1
fi

echo "Applying overlay onto $WORKTREE"

# Run string-replacement via Python helper.
python3 - "$OVERLAY_DIR/branding.yaml" "$WORKTREE" "$DRY_RUN" <<'PYEOF'
import sys, os, re, yaml
cfg_path, worktree, dry_run = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
with open(cfg_path) as f:
    cfg = yaml.safe_load(f)
count = 0
for entry in cfg.get("replacements", []):
    pattern = entry["pattern"]
    replacement = entry["replacement"]
    paths = entry.get("paths", ["**/*.kt", "**/*.xml", "**/*.gradle*", "**/AndroidManifest.xml"])
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

# Drop in compliance composables
mkdir -p "$WORKTREE/app/src/main/java/io/element/android/x/compliance"
cp -v "$OVERLAY_DIR/Compliance/"*.kt "$WORKTREE/app/src/main/java/io/element/android/x/compliance/" 2>/dev/null || true

# Drop in UnifiedPush wiring (fdroid flavor)
mkdir -p "$WORKTREE/app/src/fdroid/java/io/element/android/x/push"
cp -v "$OVERLAY_DIR/UnifiedPush/UnifiedPushConfig.kt" "$WORKTREE/app/src/fdroid/java/io/element/android/x/push/" 2>/dev/null || true

# Drop in Config defaults
mkdir -p "$WORKTREE/app/src/main/java/io/element/android/x/config"
cp -v "$OVERLAY_DIR/Config/HomeserverDefaults.kt" "$WORKTREE/app/src/main/java/io/element/android/x/config/" 2>/dev/null || true

# Drop in localized strings
for lang in values values-ro-rMD values-ru values-uk; do
    mkdir -p "$WORKTREE/app/src/main/res/$lang"
    cp -v "$OVERLAY_DIR/res/$lang/strings.xml" "$WORKTREE/app/src/main/res/$lang/" 2>/dev/null || true
done

# Append our R8 rules to the existing proguard file
if [ -f "$CLIENT_DIR/proguard-rules-mdchat.pro" ]; then
    cp -v "$CLIENT_DIR/proguard-rules-mdchat.pro" "$WORKTREE/app/proguard-rules-mdchat.pro"
fi

touch "$WORKTREE/.overlay-applied"
echo "Overlay applied."
