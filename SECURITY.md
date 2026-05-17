# Security Policy

## Reporting vulnerabilities

Email **security@md-chat.eu** with:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Any mitigations you've identified
- Whether you would like public attribution

We commit to:
- Acknowledge receipt within 48 hours
- Provide initial assessment within 5 business days
- Maintain communication throughout the resolution
- Credit you in the security advisory (unless you prefer anonymity)
- Follow the EU Cyber Resilience Act (CRA) 24-hour preliminary disclosure requirements once they enter force on 11 September 2026

## Scope

In scope:
- `server/` — Synapse fork and all its dependencies
- `client-*/` — All client applications
- `ai-layer/` — AI service stack
- `infra/` — Deployment configurations
- `*.md-chat.eu` — Production and staging services

Out of scope:
- Vulnerabilities in upstream Synapse / Element / libsignal / OpenMLS (report directly to those projects)
- Social engineering against individual maintainers
- Denial-of-service attacks (without a clear amplification factor)
- Issues only reproducible on heavily modified forks

## Disclosure timeline

We aim for 90-day responsible disclosure. We may extend or shorten this for:
- Critical vulnerabilities affecting active users (faster public disclosure)
- Complex issues requiring coordinated upstream patches (longer embargo)

## Bug bounty

We do not yet operate a paid bug bounty program. We will introduce one once grant funding allows (target: Sprint 11, Q1 2027).

## PGP key

```
[PGP key fingerprint to be added once we generate one for security@md-chat.eu]
```

## Past advisories

None yet. This file will track historical security advisories as they are issued.

## Acknowledgments

We thank all researchers who have responsibly disclosed issues. See [SECURITY-ACKNOWLEDGMENTS.md](SECURITY-ACKNOWLEDGMENTS.md) for the hall of fame.

---

*Last updated: 17 May 2026*
