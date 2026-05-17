# Contributing to MD-Chat

Thanks for your interest! MD-Chat is built by Mega Promoting SRL with a community-driven philosophy.

## Quick start

1. **Read** [README.md](README.md) and pick the component you want to contribute to.
2. **Discuss** before significant work — open an Issue or join `#md-chat:matrix.org`.
3. **Fork** the repo, branch off `main`, follow the conventions below.
4. **Submit** a PR with a clear description and link to the discussion Issue.

## Development setup

```bash
git clone https://github.com/olegchetrean/md-chat
cd md-chat

# Server (Synapse fork)
cd server && ./scripts/dev-setup.sh
# AI layer (Python)
cd ai-layer && python3.11 -m venv .venv && pip install -e ".[dev]"
# Web client
cd web && pnpm install && pnpm dev
```

See [docs/deploy.md](docs/deploy.md) for full local deploy with Docker compose.

## Code style

- **Python**: ruff + black, type hints required
- **TypeScript**: ESLint + Prettier, strict mode
- **Rust**: cargo fmt + clippy, `#![deny(warnings)]` for new crates
- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `chore:`)
- **Languages**: code + comments in English; UI copy primarily in Romanian, Russian, English

## License & sign-off

By contributing, you agree to license your contribution under:
- **AGPLv3** for `server/`, `client-*/`, `web/`
- **Apache 2.0** for `ai-layer/`
- **CC-BY-SA 4.0** for `docs/`, `brand/`, `infra/`

All commits must include `Signed-off-by: Your Name <email>` (DCO).

## Areas where we welcome help

### High-priority (Sprint 0 → 3)
- Synapse fork rebranding (AGPLv3 boilerplate)
- Element X iOS/Android fork rebranding
- Phone verification + TOTP MFA via Infobip
- EVO/MPass SAML-to-OIDC bridge

### Medium-priority (Sprint 4 → 6)
- Cronberry AI layer Synapse event adapter
- Digital Twin self-twins (refactor profile_generator for self-data)
- MSign SOAP→REST wrapper

### Long-term
- Mini-apps platform TMA-compatible runtime
- Wero / SEPA Instant integration
- MCP-first bot ecosystem
- eIDAS Wallet OpenID4VP verifier

## Reporting security issues

Email security@md-chat.eu. Do NOT open public issues for security vulnerabilities.

We follow a 90-day responsible disclosure timeline + CRA 24-hour preliminary disclosure obligations (effective 11 September 2026).

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful and constructive.

## Sweat equity / paid work

For sustained, significant contributions Mega Promoting may offer:
- Co-author credit on academic papers (NLnet, Horizon Europe outputs)
- Bonus payouts when grants land (NLnet, Sovereign Tech Fund, Prototype Fund DE)
- Future employment if MRR grows

Contact maintainer at contact@md-chat.eu for details.

## Recognition

Contributors are listed in [AUTHORS](AUTHORS) (alphabetical, opt-in). Major contributors recognized in release notes.

Welcome aboard.
