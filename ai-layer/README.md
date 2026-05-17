# md-chat-ai

> AI organizing layer for MD-Chat. Derived from the Cronberry engine (Mega Promoting internal product, licensed for use; released here under Apache 2.0).

## What it does

- **Digital Twin engine** — AI personas that respond on a user's behalf when offline. Supports `auto_reply`, `business_24_7`, `vacation` modes. Optional eIDAS attestation (Verified Authentic Twin).
- **Knowledge graph** — Neo4j-backed social graph. Computes PageRank, community detection, mutual contacts.
- **Multi-provider LLM client** — Router by MP gateway + Anthropic + OpenAI + local Llama 3.2. Aggressive caching.
- **Daily briefing** — per-user summary of overnight activity. Confidential compute.
- **Smart compose / summarization / sentiment / action items** — on-device when possible, confidential cloud (Apple PCC pattern) otherwise.
- **SaaS infrastructure** — multi-tenant API keys (`mc_*`), Stripe billing, onboarding flow.

## Architecture

```
md-chat-ai/
├── src/md_chat_ai/
│   ├── api/         Flask blueprint + request schemas
│   ├── agents/      Digital Twin engine
│   ├── graph/       Neo4j knowledge graph
│   ├── llm/         Multi-provider LLM client with fallback + cache
│   ├── memory/      Short/Long/Relationship memory
│   ├── security/    Prompt guard + GDPR helpers + rate limiter
│   └── api_mcp.py   MCP server endpoint
├── tests/           pytest suite
├── pyproject.toml
└── Dockerfile
```

## Quick start (development)

```bash
cd ai-layer
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Set up env
cp .env.example .env.local
# Edit .env.local

# Run
python -m md_chat_ai.wsgi
# Or via Docker:
docker build -t md-chat-ai . && docker run --env-file .env.local -p 5002:5002 md-chat-ai
```

## API

Base URL: `https://msg.md-chat.eu/api/ai/` (production) or `http://localhost:5002/api/` (dev)

### Health
```
GET /health        Service status + config
GET /metrics       Prometheus metrics (port 9090)
```

### Digital Twin
```
POST /twin/<user_id>/chat        Chat with twin
GET  /twin/<user_id>/profile     Get twin persona
POST /twin/<user_id>/optimize    Optimize message before sending
POST /twin/<user_id>/feedback    Learning loop
```

### Knowledge graph
```
POST /graph/build                Build social graph from Synapse events
GET  /graph/stats                Counts + summary
GET  /graph/visual               Cytoscape-compatible JSON
```

### Reports
```
POST /report/generate            Generate report from template
GET  /briefing                   Daily digest for current user
```

### SaaS (multi-tenant)
```
POST /saas/register              Generate API key
GET  /saas/usage                 Tenant usage
POST /saas/billing/checkout      Stripe checkout
```

See `docs/api.md` for full reference.

## License

**Apache License 2.0** — see [LICENSE](LICENSE).

Built on the Cronberry engine, licensed by Mega Promoting SRL for use in this open-source project.

## Status

🚧 **Scaffold** (Sprint 1). Production-grade `digital_twin.py`, `simulation/*`, `graph/*` to be ported from Cronberry over Sprint 5.
