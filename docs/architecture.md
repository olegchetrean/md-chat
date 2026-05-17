# MD-Chat Architecture

> 8-layer super-app architecture. Each layer is documented and tested independently.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│ 8. SOCIAL          stories, channels, communities           │
├─────────────────────────────────────────────────────────────┤
│ 7. COMMERCE        CRM port from Cronberry, business twins  │
├─────────────────────────────────────────────────────────────┤
│ 6. GOVERNMENT      EVO, MPass, MSign, MDelivery             │
├─────────────────────────────────────────────────────────────┤
│ 5. AI LAYER        Cronberry-derived, confidential compute  │
├─────────────────────────────────────────────────────────────┤
│ 4. APPS            TMA-compatible mini-apps + MCP bots      │
├─────────────────────────────────────────────────────────────┤
│ 3. PAYMENTS        Wero + SEPA Instant + MIA + opt TON      │
├─────────────────────────────────────────────────────────────┤
│ 2. IDENTITY        EVO + MPass + eIDAS Wallet               │
├─────────────────────────────────────────────────────────────┤
│ 1. TRANSPORT       E2EE Matrix + libsignal + OpenMLS        │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1 — Transport

- **Server**: Matrix Synapse fork (AGPLv3). Custom branding, Moldova/EU defaults.
- **1:1 messaging**: libsignal-derived (PQXDH + Triple Ratchet + Sesame multi-device).
- **Group messaging**: OpenMLS RFC 9420, ciphersuite `MLS_MLKEM768_X25519_AES256GCM_MLDSA65`.
- **Metadata reduction**: Sealed Sender pattern.
- **Federation**: closed list initially (allowlist); MIMI-ready for EU interop 2027.

## Layer 2 — Identity

- **Default**: username + phone-OTP via Infobip + TOTP + PIN-derived backup (Signal SVR3 pattern).
- **Hardware**: iOS Secure Enclave / Android StrongBox for root keys.
- **Verified by EVO** (opt-in): MPass SAML 2.0 → OIDC bridge. Releases only `verified`, `age_band`, `prenume`.
- **eIDAS Wallet** (2027+): OpenID4VP verifier, cross-border EU identity.

## Layer 3 — Payments

- **Primary**: Wero (EPI) — EU instant payments, 0% user-to-user.
- **Fallback**: SEPA Instant via Adyen/Mollie.
- **Moldova**: MIA Instant for MDL transfers.
- **Crypto (optional)**: TON wallet behind opt-in screen.
- **PSD3 + MiCA compliant** at scale.

## Layer 4 — Apps

- **Mini-apps platform**: Telegram-Mini-App-compatible runtime (WXML-style sandbox).
- **Bot platform**: each bot is also an MCP server (Model Context Protocol).
- **Distribution**: in-app marketplace + QR codes + search.
- **Revenue share**: 15% (undercut Telegram Stars 30%, Apple 30%, Google 30%).

## Layer 5 — AI Layer

Derived from Cronberry, open-sourced under Apache 2.0.

- **Digital Twin engine** — self-twin AI personas, eIDAS-attested for Verified Authentic Twin.
- **Knowledge Graph** — Neo4j, PageRank, community detection.
- **Confidential AI** — on-device Llama 3.2 3B + cloud Router-by-MP with TEE attestation (Apple PCC pattern).
- **Smart compose, summarization, sentiment, action items** — defaults on-device.

## Layer 6 — Government

- **MSign** — REST wrapper over SOAP, qualified e-signature.
- **MDelivery** — registered electronic delivery.
- **State services tab** — Fisc, CNAS, CNAM, Vamă mini-apps.
- **eIDAS interop** for EU citizens.

## Layer 7 — Commerce

- **Cronberry CRM port** — lead pipeline, deal tracking, business profile, customer service inbox.
- **Verified business badge** — KYB Know Your Business.
- **Catalogues + payments** — full SME storefront.

## Layer 8 — Social

- **Stories** (24h ephemeral, opt-in).
- **Channels** (broadcast, public/private).
- **Communities** (WhatsApp Communities-style umbrella).
- **Spaces** (Matrix Spaces hierarchy).

## Cross-cutting

- **AGPLv3** for server + clients.
- **Apache 2.0** for AI layer.
- **CC-BY-SA 4.0** for docs, brand, infra.
- **EU-compliance from Day 1**: GDPR + AI Act + eEvidence + CRA + Moldova Law 195/2024.
- **No vendor lock-in**: replaceable sub-processors, public sub-processor list with 30-day notice.

## See also

- [Deploy guide](deploy.md)
- [Compliance](compliance.md)
- [Roadmap](roadmap.md)
