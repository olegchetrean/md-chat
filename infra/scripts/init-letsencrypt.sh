#!/usr/bin/env bash
# Initialize Let's Encrypt certificates for MD-Chat. Run ONCE on first deploy.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../docker"

DOMAINS=(msg.md-chat.eu md-chat.eu www.md-chat.eu)
EMAIL="${LETSENCRYPT_EMAIL:-security@md-chat.eu}"

echo "Starting nginx for ACME challenge..."
docker compose up -d nginx

for DOMAIN in "${DOMAINS[@]}"; do
    echo "Requesting cert for $DOMAIN..."
    docker compose run --rm certbot certonly \
        --webroot \
        -w /var/www/acme-challenge \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --non-interactive || {
        echo "⚠️  Cert request for $DOMAIN failed, continuing..."
    }
done

echo "Reloading nginx..."
docker compose restart nginx

echo "✅ Let's Encrypt setup complete. Auto-renewal every 12h via certbot container."
