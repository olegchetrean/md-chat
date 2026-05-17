# MD-Chat

> EU sovereign messenger built from $0 budget by Mega Promoting SRL (Moldova).
> Fork of Matrix Synapse + Element X + Cronberry AI layer.
> AGPLv3 server / Apache 2.0 AI layer.

## Status

🚧 **Bootstrap phase** — repo public 18 May 2026. NLnet NGI Zero application submitted 30 May 2026. MVP target Q4 2026.

## Vision

A sovereign EU messenger that combines:
- **E2EE messaging** (libsignal + MLS RFC 9420 + PQXDH post-quantum)
- **Sovereign identity** (EVO/MPass for Moldova, eIDAS Wallet for EU)
- **Native AI** (Digital Twins, smart compose, summarization — confidential compute)
- **Super-app capabilities** (mini-apps platform, MCP-first bot ecosystem)
- **Payments** (Wero + SEPA Instant + MIA Instant Moldova)
- **Government services** (MSign, MDelivery, Fisc, CNAS integration)
- **EU jurisdiction by default** — adequacy-aware, eEvidence-compliant, AI Act-compliant from Day 1

## Architecture (8 layers)

```
8. Social (stories, channels, communities)
7. Commerce (CRM port from Cronberry, business twins)
6. Government (EVO/MPass/MSign/MDelivery)
5. AI Organizing Layer (Cronberry-derived AI brain)
4. Apps (TMA-compatible mini-apps, MCP bots)
3. Payments (Wero, SEPA Instant, MIA)
2. Identity (EVO, MPass, eIDAS Wallet, username+phone+TOTP)
1. Transport (E2EE Matrix/Synapse fork, libsignal, OpenMLS)
```

## Repo structure

```
md-chat/
├── server/         Synapse fork + Cronberry AI sidecar
├── client-ios/     Element X iOS fork
├── client-android/ Element X Android fork
├── web/            Element Web fork (Next.js wrapper)
├── ai-layer/       Cronberry-derived AI services (Python/Flask)
├── infra/          Docker compose, nginx, deployment scripts
├── docs/           Architecture, API, deploy guides
└── brand/          Logo, palette, voice/tone guidelines
```

## Hard deadlines

- **30 May 2026** — NLnet NGI Zero Commons Fund application
- **2 August 2026** — AI Act Art 50 transparency disclosure
- **18 August 2026** — eEvidence Regulation production order portal
- **11 September 2026** — CRA 24h vulnerability disclosure obligations

## License

- `server/` — AGPLv3 (downstream of Synapse)
- `client-ios/`, `client-android/`, `web/` — AGPLv3 (downstream of Element)
- `ai-layer/` — Apache 2.0 (new code derived from Cronberry under intra-Mega license)
- `infra/`, `docs/`, `brand/` — CC-BY-SA 4.0

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Contact

- Maintainer: Mega Promoting SRL, Moldova
- Email: contact@md-chat.eu
- Matrix: `#md-chat:matrix.org`
- Mastodon: `@mdchat@fosstodon.org`

## Documentation

- [Architecture](docs/architecture.md)
- [Deploy](docs/deploy.md)
- [Compliance](docs/compliance.md)
- [Roadmap](docs/roadmap.md)
