# MD-Chat Compliance

> Designed for EU regulatory compliance from Day 1.

## Current obligations

| Regulation | In force | Status |
|-----------|----------|--------|
| GDPR (EU 2016/679) | Active | Privacy Notice + DPIA + ROPA documented |
| Moldova Law 195/2024 | 23 Aug 2026 | CNPDCP registration pending |
| AI Act Article 50 | 2 Aug 2026 | Disclosure in voice + chat AI built-in |
| AI Act GPAI | 2 Aug 2026 | Model cards documented per-feature |
| eEvidence Regulation | 18 Aug 2026 | 24/7 portal scheduled, EU Rep contracted |
| Cyber Resilience Act — disclosure | 11 Sep 2026 | security@md-chat.eu live, security.txt published |
| Cyber Resilience Act — full | 11 Dec 2027 | CE marking + SBOM pipeline planned |
| DSA (if 45M MAU) | Active | Below threshold; will revisit at scale |
| DMA interop (Article 7) | Active | Voluntary participation; MIMI-ready architecture |

## Privacy by Design

- E2EE by default. No content visibility to operator.
- No phone number required (username default).
- Hardware-backed key storage (Secure Enclave / StrongBox).
- Post-quantum hybrid crypto (PQXDH + PQ-MLS).
- Sealed Sender (Signal pattern) for metadata reduction.
- Confidential compute for AI features (Apple PCC pattern).

## Operator
- **Controller**: Mega Promoting SRL, Chișinău, Moldova (IT Park)
- **DPO**: dpo@megapromoting.com
- **EU Representative (Art 27)**: Prighter SARL, Brussels, Belgium — eu-rep@md-chat.eu
- **Tax regime**: Moldova IT Park (7%)

## Sub-processors

Current list at https://md-chat.eu/legal/sub-processors

Notable:
- Hetzner (DE) — hosting
- Infobip (HR) — SMS
- Brevo (FR) — email
- Apple/Google — push notifications (US, DPF adequacy)
- Stripe Payments Europe (IE) — billing

30-day notice for any changes.

## DPIA

See [docs/dpia.md](dpia.md) for full DPIA (to be added).

## ROPA

See [docs/ropa.md](ropa.md) for full ROPA (to be added).

## Data subject rights

- **Access** (Art 15): https://md-chat.eu/data/export
- **Erasure** (Art 17): https://md-chat.eu/data/delete (30-day grace period)
- **Portability** (Art 20): JSON export
- **Rectification, Restriction, Objection**: in-app settings + email dsr@md-chat.eu
- **30-day SLA** (extendable to 60 days if complex)

## Children

- Minimum age: 16 (Moldova + EU baseline)
- Age gate: neutral, no nudges
- No profiling of minors for marketing

## Security

- E2EE by default
- TLS 1.3 only
- HSTS + ECH
- Pen testing annually (post-grant funding)
- 24-hour vulnerability preliminary disclosure (CRA-aligned)
- Public security policy: [SECURITY.md](../SECURITY.md)
- Bug bounty: planned post-Sprint 11

## Lawful access

We follow the **eEvidence Regulation** (EU 2023/1543) from 18 August 2026.

- Production orders: 24/7 portal at https://md-chat.eu/legal/eu-evidence
- Preservation orders: same portal
- Internal triage decision tree documented
- EU Representative handles initial intake
- Public transparency report: bi-annual

## Encryption — public stance

We will not introduce client-side scanning (CSAR / "Chat Control") even if mandated voluntarily.

We will comply with court-issued production orders to the extent technically possible — given our E2EE architecture, this is limited to metadata, account data, and IP logs (which we minimize to /24 prefixes and 6-month retention).

## See also

- [Privacy Notice](https://md-chat.eu/privacy)
- [Terms of Service](https://md-chat.eu/terms)
- [Sub-processors](https://md-chat.eu/legal/sub-processors)
- [Security policy](../SECURITY.md)
- [eEvidence portal](https://md-chat.eu/legal/eu-evidence)
