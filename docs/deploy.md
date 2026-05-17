# MD-Chat Deployment Guide

## Prerequisites

- Linux server (Debian 12 / Ubuntu 24.04 LTS recommended)
- Docker Engine 26+ with Docker Compose plugin
- Minimum: 4 GB RAM, 2 vCPU, 40 GB SSD (handles 0-1000 users MVP)
- Recommended at scale: 8 GB RAM, 4 vCPU, 200 GB SSD
- DNS access for domain (`md-chat.eu` family)
- 80/443/8448 ports open

## Quick deploy

```bash
git clone https://github.com/olegchetrean/md-chat
cd md-chat

# 1. Configure environment
cp infra/docker/.env.example infra/docker/.env
$EDITOR infra/docker/.env  # fill in passwords + API keys

# 2. Initialize Let's Encrypt certs (first time only)
infra/scripts/init-letsencrypt.sh

# 3. Bring up the stack
infra/scripts/deploy.sh up

# 4. Verify
curl https://msg.md-chat.eu/_matrix/client/versions
curl https://md-chat.eu/
```

## DNS configuration

| Record | Name | Value | Notes |
|--------|------|-------|-------|
| A | @ | <server-ip> | Apex |
| A | www | <server-ip> | Aliased to apex |
| A | msg | <server-ip> | Matrix homeserver |
| SRV | _matrix._tcp.md-chat.eu | 10 0 8448 msg.md-chat.eu | Federation |
| CAA | @ | 0 issue "letsencrypt.org" | Limit CA |
| TXT | @ | "v=spf1 -all" | No outbound mail from apex |

CDN (Cloudflare): DNS-only (gray cloud), NOT proxied (Matrix federation needs direct TCP on 8448).

## Operations

```bash
# View logs
infra/scripts/deploy.sh logs synapse
infra/scripts/deploy.sh logs ai-layer

# Restart a service
infra/scripts/deploy.sh restart synapse

# Backup (run via cron daily at 03:00)
infra/scripts/deploy.sh backup

# Stop / start
infra/scripts/deploy.sh down
infra/scripts/deploy.sh up
```

## Cron job for backups

```cron
0 3 * * * cd /opt/md-chat && infra/scripts/deploy.sh backup >> /var/log/mdchat-backup.log 2>&1
```

## Resource sizing

| Stage | Users | RAM | CPU | Disk | Hetzner SKU |
|-------|-------|-----|-----|------|-------------|
| MVP | 0-1k | 4 GB | 2 vCPU | 40 GB | CX22 (€4.49/mo) |
| Beta | 1-10k | 8 GB | 4 vCPU | 100 GB | CCX23 (~€15/mo) |
| Growth | 10-100k | 32 GB | 8 vCPU | 400 GB | AX41 (~€80/mo) |
| Scale | 100k-1M | 64 GB | 16 vCPU | 1 TB | AX-line dedicated (€150-300/mo) |

## Monitoring

- Prometheus scrape: `http://localhost:9090`
- Grafana dashboards: pending (Sprint 11)
- Sentry: optional `SENTRY_DSN` env var
- Status page: `status.md-chat.eu` (Sprint 11)

## Troubleshooting

### Synapse won't start
- Check `infra/scripts/deploy.sh logs synapse` for errors
- Ensure `homeserver.yaml` server_name matches DNS

### Federation broken
- Test at https://federationtester.matrix.org/
- Ensure port 8448 is open in firewall + nginx listening

### AI layer unhealthy
- Check `/api/health` returns 200
- Ensure Neo4j is up (`docker compose logs neo4j`)
- Verify Router by MP API key (`ROUTER_API_KEY`)

### Let's Encrypt rate-limited
- Use `--staging` flag in `init-letsencrypt.sh` to test
- Lifetime certs: 90 days, auto-renew every 12h via certbot container
