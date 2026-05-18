# Changelog

All notable changes to MD-Chat are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (placeholder for next release notes)

### Fixed
- (placeholder)

---

## [0.1.0-alpha] — 2026-05-18

**First public alpha. Bootstrap milestone. Not for production use.**

This release establishes the project skeleton, the AI-layer port from
Cronberry, the EU compliance scaffolding (GDPR / AI Act Art 50 / eEvidence /
CRA), and the marketing + brand identity. Server forks (Synapse, Element X)
are documented as fork plans but the actual rebrand has not yet started.

### Added — AI layer (`ai-layer/`)
- **Digital Twin engine** ported from Cronberry — self-twin mode, AI Act Art 50
  disclosure baked in, `revoke()` (Art 22), audit log, eIDAS attestation hook,
  3 new modes (`auto_reply`, `business_24_7`, `vacation`)
- **Knowledge graph** ported — Neo4j backend, 10-entity / 8-edge MD-Chat
  ontology with 3 consent tiers (public/friends/private), Synapse event adapter
- **Multi-provider LLM client** — Router by MP-first, on-device → Anthropic →
  OpenAI fallback chain, Anthropic prompt caching (~80% cost reduction),
  cost tracking in client-facing US cents
- **Sync compatibility shim** — `LLMClient.chat()` / `chat_json()` for
  Cronberry-style sync callers (digital twin, optimizer)
- **Security stack** — `PromptGuard` with prompt-injection / canary / PII
  defenses, namespaced `RateLimiter` (signup/twin-chat/briefing), `GDPRManager`
  with Art 15 export + Art 17 erasure (90-day grace + immutable erasure log),
  `AIDisclosure` (Art 50) enforcement helper, `AISafetyFilter`,
  Moldova IDNP detector
- **Reports + briefings** — 9 templates × RO/RU/EN = 27 variants; `DailyBriefing`
  digest; PII redaction; AI Act footer; `compute_backend` metadata
- **Auth module** — phone OTP via Infobip (port of Router by MP TS service),
  TOTP RFC 6238 with 8 backup codes, PIN backup with Argon2id + AES-256-GCM
  (Signal SVR3 pattern stub)
- **eEvidence portal** (EU Reg 2023/1543) — `ProductionOrderPortal`,
  `AuditRegister` with SHA-256 hash chain, 8 Art 12 refusal grounds,
  8-hour emergency SLA, internal-token auth on respond/register endpoints
- **MPass / OIDC bridge** — SAML 2.0 SP + internal SAML→OIDC bridge + PKCE
  + JWKS; IDNP refused by default; MSign SOAP client wrapped as REST

### Added — Flask app
- Blueprints registered: `/api/health`, `/api/ready`, `/api/v1/auth/*`,
  `/api/v1/legal/eevidence/*`, `/api/v1/identity/*`, `/oidc/*`,
  `/.well-known/openid-configuration` — 25 routes total
- Security middleware (`ErrorHandler`) attached at app boot

### Added — Infrastructure (`infra/`)
- Docker compose: 8 services (Postgres, Redis, Neo4j, Synapse,
  ai-layer, nginx, certbot, Prometheus)
- nginx vhosts for `msg.md-chat.eu`, `md-chat.eu`, federation port 8448
- Let's Encrypt automation via certbot container (12 h renew)
- Synapse `homeserver.yaml` — E2EE default, gated registration, retention
  180 d, federation allowlist
- Deploy + init-letsencrypt + dev-setup scripts (executable)
- Prometheus scrape config (Synapse + ai-layer)

### Added — Landing site (`infra/landing/`)
- `index.html` — Tailwind production page (5 sections + footer)
- `privacy.html`, `terms.html`, `security.html` — themed HTML pages
- `robots.txt`, `sitemap.xml`, `.well-known/security.txt`
- Blog launch posts (RO + EN ~1.7k cuv each)
- Show HN copy, Mastodon 6-toot thread, LinkedIn post,
  10 personalized B2B email drafts, 4 letters of intent
  (AGE WE BUILD, Moldova IT Park, UTM, MSA Credit pilot),
  press inquiry template (EN/RO/RU)

### Added — Brand (`brand/`)
- 6 SVG logo variants (primary, mono-light, mono-dark, wordmark, app-icon,
  favicon) — paths-only, no font dependency
- `colors.css`, `typography.css` (Inter + JetBrains Mono)
- Brand README, voice & tone guide, OG image spec, social card spec
- Press releases RO + EN + RU (~420 cuv each, Cyrillic native for RU)

### Added — Docs (`docs/`)
- `architecture.md` — 8-layer architecture (Transport → Identity → Payments
  → Apps → AI → Government → Commerce → Social)
- `deploy.md`, `compliance.md`, `roadmap.md`, `testing.md`,
  `release-process.md`
- **GDPR production docs** (CC-BY-SA 4.0, ~19 k cuv):
  `privacy-notice.md`, `dpia.md`, `ropa.md`, `sub-processors.md`,
  `dsr-process.md`, `breach-response.md`, `terms-of-service.md`,
  `legal-index.md`, `eevidence-runbook.md`, `mpass-integration.md`
- **Fork plans**: `synapse-rebrand-plan.md` (~5k cuv),
  `element-x-ios-fork-plan.md` (~5.4k cuv),
  `element-x-android-fork-plan.md` (~4.2k cuv)
- `issues-to-create.md` — 6 GitHub issue drafts for community batch publish

### Added — CI / Security / Release
- `.github/workflows/ci.yml` — ruff + black + mypy (continue-on-error) +
  pytest with coverage gate (currently 65 %, target 70 %)
- `.github/workflows/security.yml` — bandit (SARIF) + safety + pip-audit
  + trivy (config + image) + gitleaks; weekly cron
- `.github/workflows/release.yml` — workflow_dispatch + tag push; semver
  validation; auto-changelog
- `.github/workflows/sbom.yml` — CycloneDX 1.5 SBOM (Python + container)
  attached to releases (CRA-aligned)
- `.github/CODEOWNERS`
- `.github/dependabot.yml` — weekly pip + docker + actions updates

### Tests
- **252 tests passing** (8 modules + integration + smoke + compliance)
- Coverage: **69 %** (target 70 % by Sprint 1 close)

### Known limitations
- Server forks (`server/`, `client-ios/`, `client-android/`, `web/`) are
  empty placeholders — actual upstream forks land in Sprint 1
- `wsgi.py` runs Flask dev server; production deploy must front with
  gunicorn / uvicorn (deferred to Sprint 1)
- MPass / MSign / EVO integration is inert until AGE Moldova approves the
  WE BUILD relying-party slot
- Coverage gate temporarily relaxed to 65 % during Sprint 0 (post-port);
  restores to 70 % by Sprint 1 close

### Compliance milestones (planned)
- 2 Aug 2026 — AI Act Art 50 transparency enforceable
- 18 Aug 2026 — eEvidence Regulation production-order portal mandatory
- 23 Aug 2026 — Moldova Law 195/2024 alignment
- 11 Sep 2026 — CRA 24 h vulnerability disclosure obligation
- 11 Dec 2027 — CRA full conformity (CE marking + SBOM)

[Unreleased]: https://github.com/olegchetrean/md-chat/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/olegchetrean/md-chat/releases/tag/v0.1.0-alpha
