<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 Mega Promoting SRL
Author: Oleg Chetrean <oleg@megapromoting.com>
Target venue: news.ycombinator.com
Submission date: D7-D9 of Sprint 0 (24-26 May 2026)
-->

# Show HN submission &mdash; MD-Chat

**URL field**: https://md-chat.eu

**Title** (78 chars, under HN's 80-char limit):
```
Show HN: MD-Chat – a $0-budget EU sovereign messenger (Matrix + AI + EVO ID)
```

---

## Body (~400 words)

Hi HN,

We're Mega Promoting, a small (8-person) tech shop in Moldova. Today we're publishing the code for MD-Chat: a sovereign EU messenger we'll spend the next 18 months building on a zero-cash budget, EU grants, and sweat equity. Repo: https://github.com/olegchetrean/md-chat. The landing page above explains the why; this post is for the how.

The wedge: every existing privacy-first FOSS messenger (Signal, Threema, Wire, Olvid, Element, SimpleX, Session) explicitly refuses to integrate AI features, because exposing plaintext to an AI breaks the threat model. Meanwhile every commercial messenger (iMessage, WhatsApp, Telegram Premium) is racing to ship AI without solving the same problem. Apple's Private Cloud Compute (June 2024) and Meta's Private Processing (October 2024) showed how it can be done: stateless TEEs, public attestation, externally auditable images. We're applying that pattern to a Matrix-based fork.

Stack:
- Synapse fork (Python/Twisted) + Element X forks (Rust/Swift/Kotlin), all AGPLv3
- libsignal + MLS RFC 9420 + PQXDH (NIST FIPS 203 ML-KEM)
- Confidential-compute AI layer derived from our existing conversation-analytics product Cronberry, relicensed Apache 2.0, running on AMD SEV-SNP and (later) Intel TDX with public attestation
- Native EVO/MPass identity (Moldova's gov SSO), eIDAS 2.0 Wallet ready (OpenID4VP)
- MCP-first bot ecosystem &mdash; every bot is also a Model Context Protocol server, so external LLMs can call them with user consent
- Wero + SEPA Instant for payments

What's actually different from "yet another Matrix fork":
1. First Matrix-based fork shipping with AI Act Art 50 disclosures, eEvidence 24/7 portal, and CRA-grade vulnerability handling from day one (those EU rules go into force Aug&ndash;Sep 2026).
2. First messenger with a public, signed kill-switch: if at month 18 we don't have €50k in grants AND €3k MRR, we shut down honestly, document, and hand the codebase to whoever wants it. The commitment is in the repo, not in marketing copy.
3. Funded by a transparent grant ladder &mdash; NLnet NGI Zero Commons (€30k, deadline 30 May), Prototype Fund DE (Jan 2027), Sovereign Tech Fund, Horizon Europe.

What we'd love feedback on:
- The PQXDH integration plan (we're behind Signal's reference impl &mdash; advice welcome)
- The confidential-compute attestation chain (we want it reproducible; help with that is gold)
- The "Verified Authentic Digital Twin" spec we plan to submit as an IETF draft
- Any EU sovereign-tech contacts you'd suggest

Hard things we won't pretend to solve overnight: federation policy at scale, push notifications without leaking metadata to Apple/Google, and the moderation/lawful-access tension. We document our thinking openly &mdash; including where we don't have an answer yet.

Mastodon: @mdchat@fosstodon.org. Matrix: #md-chat:matrix.org. Press: press@md-chat.eu.

&mdash; Oleg / Mega Promoting

---

## Notes for the submitter (Oleg)

- **Best window**: Tuesday or Wednesday, 14:00&ndash;16:00 UTC (09:00&ndash;11:00 ET). Avoid Monday morning, Friday afternoon.
- **First-hour discipline**: be present in the comments; reply within minutes; lead with substance, not promotion. Treat every critical reply as an audit.
- **Do not**: ask friends to upvote, post the same URL twice, or write "thanks for the feedback" without a substantive answer.
- **Pre-flight checklist**: README is concise; repo has a tagged release v0.1.0; SECURITY.md fingerprint is correct; the live demo (if any) is up; the rate-limiter is configured (HN hug-of-death can hit ~100 req/s).
- **Follow-up post**: write a "What we learned from Show HN" post 7&ndash;10 days later, with stats and lessons. Honest, not victory-lapping.

---

## Anticipated tough questions &mdash; prepared honest answers

**Q: How is this not just another Matrix fork?**
A: We're not changing the protocol; we're adding three things on top (confidential AI, EU identity, MCP bots) and committing to compliance from day one. Most Matrix deployments postpone compliance work until they have customers. We're doing the opposite.

**Q: Eight people, zero budget, 18 months &mdash; isn't that overoptimistic?**
A: Yes, and that's why we have the kill-switch. We are not promising success; we are promising transparency about failure. The grant ladder is realistic (NLnet alone funds 80&ndash;120 projects a year at this scale; we have a strong narrative and prior FOSS work via Cronberry).

**Q: Why Moldova?**
A: Because we are here, because we are an EU candidate without a sovereign messenger, and because IT Park gives us a clean tax/legal/HR footprint as a Moldovan company that can serve EU customers. We are not "outsourcing to cheap labour"; we are the team.

**Q: How can AI features coexist with E2EE?**
A: Through confidential compute. The user's client encrypts the input with a key derived from a TEE attestation; the TEE decrypts inside the enclave, runs the model, and returns the result encrypted to the user. Apple PCC is the canonical reference. Our implementation will be reproducible from source.

**Q: What stops you from being co-opted by the Moldovan state?**
A: We're a private SRL, our DPO is independent, our EU Representative (Prighter) is independent, the code is open, the cryptography is standard, and we publish a Transparency Report. Co-option requires either changing the code (publicly visible) or compelling us to act against the code (which we cannot do without auditable evidence). The threat is real; the design refuses it.
