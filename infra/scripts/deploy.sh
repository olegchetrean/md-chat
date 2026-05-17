#!/usr/bin/env bash
# MD-Chat deploy script.
# Usage: ./deploy.sh [up|down|rebuild|logs|backup|status]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/../docker"
BACKUP_DIR="${MDCHAT_BACKUP_DIR:-/var/backups/md-chat}"

cd "$DOCKER_DIR"

if [[ ! -f .env ]]; then
    echo "❌ .env file missing. Copy .env.example to .env and fill in values."
    exit 1
fi

ACTION="${1:-status}"

case "$ACTION" in
    up)
        echo "🚀 Starting MD-Chat stack..."
        docker compose pull
        docker compose build --pull
        docker compose up -d
        echo
        echo "✅ Stack running."
        docker compose ps
        ;;
    down)
        echo "🛑 Stopping MD-Chat stack..."
        docker compose down
        ;;
    restart)
        docker compose restart "${2:-}"
        ;;
    rebuild)
        echo "🔧 Rebuilding services..."
        docker compose build --no-cache
        docker compose up -d
        ;;
    logs)
        docker compose logs -f --tail=200 "${2:-}"
        ;;
    status|ps)
        docker compose ps
        ;;
    backup)
        DATE=$(date +%Y%m%d-%H%M%S)
        TARGET="$BACKUP_DIR/$DATE"
        mkdir -p "$TARGET"
        echo "💾 Backing up to $TARGET..."
        docker compose exec -T postgres pg_dump -U mdchat_synapse mdchat_synapse > "$TARGET/synapse.sql"
        docker compose exec -T neo4j neo4j-admin database dump --database=neo4j --to-stdout > "$TARGET/neo4j.dump"
        echo "✅ Backup complete."
        ;;
    exec)
        shift
        docker compose exec "$@"
        ;;
    *)
        echo "Usage: $0 {up|down|restart|rebuild|logs|status|backup|exec}"
        exit 1
        ;;
esac
