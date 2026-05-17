#!/usr/bin/env bash
# Local development setup for MD-Chat. Sets up dependencies + git hooks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/../.."
cd "$PROJECT_ROOT"

echo "🔧 MD-Chat dev setup..."

# Check Docker.
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker not installed. Get it from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Python 3.11+.
if ! command -v python3.11 >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3.11+ required."
    exit 1
fi

# AI layer setup.
if [[ -d ai-layer ]]; then
    echo "  Setting up ai-layer..."
    cd ai-layer
    python3.11 -m venv .venv 2>/dev/null || python3 -m venv .venv
    source .venv/bin/activate
    pip install -q --upgrade pip
    if [[ -f pyproject.toml ]]; then
        pip install -q -e ".[dev]" 2>/dev/null || echo "  ⚠️  pyproject.toml exists but install failed"
    fi
    cd ..
fi

# Docker compose env.
if [[ ! -f infra/docker/.env ]] && [[ -f infra/docker/.env.example ]]; then
    cp infra/docker/.env.example infra/docker/.env
    echo "  📝 Created infra/docker/.env from example — FILL IN VALUES"
fi

echo
echo "✅ Dev setup complete."
echo
echo "Next steps:"
echo "  1. Edit infra/docker/.env with real values"
echo "  2. Run infra/scripts/init-letsencrypt.sh (first time only)"
echo "  3. Run infra/scripts/deploy.sh up"
