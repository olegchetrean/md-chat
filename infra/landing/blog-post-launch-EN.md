<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 Mega Promoting SRL
Author: Oleg Chetrean <oleg@megapromoting.com>
First published: megapromoting.com/blog/md-chat-launch-en
-->

# Why we are building a sovereign messenger in Moldova

*Oleg Chetrean &middot; Chișinău &middot; 18 May 2026*

On 24 August 2024, Pavel Durov was detained at Le Bourget airport in Paris. Four days later he was placed under judicial supervision and was no longer allowed to leave France without authorization. In the month that followed, Telegram announced "closer cooperation" with authorities, changed its moderation policies, started handing over phone numbers and IP addresses to legal requests, and the relationship between the platform and its users quietly slid into territory where no one really guarantees anything about anything any more.

For users in the Republic of Moldova — and our diaspora of more than a million people — that moment was more than a tech-news story. Telegram is, for better or worse, the backbone of public communication in Moldova: news channels, civic organisations, neighbourhood groups, small business, even institutions. Viber carries a share of personal communication and some of the public notifications (Bureau of Statistics, MAIB bank, MoldTelecom). WhatsApp covers the EU diaspora. And across all these platforms, we hold the same position: customer, not owner.

We have been an EU candidate country since 2022. We are the only EU candidate without a sovereign messenger. France has Tchap, mandatory for civil servants (more than 600,000 users). Germany has BwMessenger for the armed forces and gematik TI-Messenger for the health system (74 million patients). Belgium has BEAM. Italy has IO. Ukraine has Diia, integrated with digital identity. Estonia has e-Estonia. Cyprus, Lithuania, Slovenia — every one of them has at least one official communication layer where the state controls keys and jurisdiction.

We have none of this.

In 2026, that stopped being a curiosity and became a national-security risk.

## What "sovereign" means &mdash; and what it does not

Before I write what we are doing, I want to be very clear about what "sovereign" does **not** mean. It does not mean building a state Telegram. It does not mean domestic surveillance. It does not mean a backdoor. It does not mean "all Moldovan communication on a server controlled by someone in Chișinău". All of those options are fundamentally incompatible with fundamental rights, with GDPR, and with how an EU member state (or candidate) must treat its citizens' data.

Sovereign, in our usage, means four concrete and verifiable things:

1. **Clear jurisdiction**: operator registered in the EU or in a candidate country, with an EU Representative under Article 27 GDPR, with a designated DPO, with a known and public legal-scope-of-application.
2. **Open source**: server code, client code, and AI-layer code published under FOSS licences (AGPLv3 + Apache 2.0 + CC-BY-SA for docs). Anyone can audit. Anyone can fork.
3. **End-to-end encryption with no exceptions**: standard protocols (Signal Protocol, MLS RFC 9420, PQXDH post-quantum), audited implementations, no master keys, no "government silver key", no content moderation on encrypted content.
4. **Optional verifiable identity**: the user decides whether to attach an EVO/MPass identity to their account, without being forced and without exposing their personal identification number (IDNP).

That is what we are building. And we are building it on labour, not money.

## MD-Chat: the architecture, briefly

MD-Chat is a fork of the Matrix protocol — we chose Matrix because it is the only open messaging protocol with mature federation, with E2EE audited by Cure53 and NCC Group, with an active community (Element, Synapse, Conduit, Dendrite), and which has already been adopted by EU member states (Tchap, BwMessenger and TI-Messenger are all Matrix-based). We are not reinventing the wheel where others have already done the hard work.

On top of Matrix we build four new things:

- **A confidential AI layer**, derived from Cronberry (our existing conversation-analytics product) and relicenced under Apache 2.0. It runs summaries, smart compose, sentiment, and a personal Digital Twin — all in confidential compute (the Apple Private Cloud Compute pattern), with public attestation. In plain English: AI can help the user, but we (the operator) never see what the AI processes.
- **Native EVO / MPass / MSign integration**. Users in Moldova can receive a "Verified by EVO" badge at signup, without us learning their IDNP. Later (Q1 2027) we will support the eIDAS 2.0 Digital Identity Wallet, which becomes mandatory across the EU from autumn 2027.
- **MCP-first bot ecosystem**: every bot in MD-Chat is also a Model Context Protocol server, meaning it can be called from outside MD-Chat — by Claude, by GPT, by any LLM. The inverse of the WeChat walled garden. We do not want to be a trap.
- **EU compliance from day one**: AI Act art. 50 (in force 2 August 2026), eEvidence Regulation (18 August 2026), Cyber Resilience Act (11 September 2026), GDPR (already), Moldova Law 195/2024 (23 August 2026). We are the only messenger launching this year that ships with all of these obligations already implemented, not retrofitted.

All components are already visible at [github.com/olegchetrean/md-chat](https://github.com/olegchetrean/md-chat). The repository goes public on 18 May 2026, simultaneously with this post.

## Why now, why us

Here I have to be honest, because I do not want to give the impression that Mega Promoting SRL is a hundred-person company launching a billion-euro product. We are eight people in Chișinău with four products in production: aichat.md (AI chatbot platform), Cronberry (conversation analytics), Kallina (voice assistant), and Router by MP (LLM gateway). Our monthly revenue is in the few thousand euros. We have debt. We have a recovery plan. And we are still launching MD-Chat — because, paradoxically, our financial position is exactly what makes us the right partner for a sovereign FOSS project.

Here is why.

First, we know the stack. Aichat.md handles more than 100,000 messages a day with AI agents integrated into WhatsApp, Facebook, Telegram and SMS, with dozens of Moldovan companies as customers. Cronberry analyses those conversations. Kallina runs voice agents for ATMs, MSA Credit (deals in progress), hospitals. The confidential AI stack in MD-Chat is not a blank sheet — it is a relicensing of a system that is in production today.

Second, we are already GDPR-compliant and have completed an internal audit which identified and closed 18 of 23 gaps (the internal report is public). We have DPIA process, ROPA, DSR registers, an EU Representative agreement signed with Prighter. That is not something you build overnight.

Third, we launch on a zero budget. We build on existing cloud-credit offers (Azure for R&D, Hetzner for prod, Bunny.net for CDN), on sweat equity, and on a European funding ladder: NLnet NGI Zero Commons (€30k, deadline 30 May 2026), Prototype Fund DE (€47k, January 2027), Sovereign Tech Fund (€100k+, spring 2027), Horizon Europe (consortium, autumn 2027).

Fourth — and this is the part I want to emphasise — we have a **public kill-switch at month 18**. If by November 2027 we have neither €50,000 in committed EU grants **nor** €3,000 of MRR (real B2B customers, paying with an invoice), we shut down honestly. We document, hand the code over to the community, and return to the core business. This is not an optimistic promise; it is a decision taken in the Mega Promoting internal council and recorded publicly. If we launch a messenger that no one wants to pay for and that the EU does not want to fund as sovereign tech, that is the signal that we were not the right ones to build it.

## Public roadmap

- **Q3 2026 (months 0&ndash;3)**: public repo (this week), AI layer published under Apache 2.0, NLnet application submitted, AI Act + eEvidence compliance functional, first 5 B2B pilots from the warm Mega base.
- **Q4 2026 (months 4&ndash;6)**: beta with phone + TOTP + EVO/MPass auth, first 5&ndash;10 paying customers, Prototype Fund DE application.
- **Q1 2027 (months 7&ndash;9)**: confidential AI on group chats, Digital Twin self-mode, IETF draft for "Verified Authentic Twin" submitted for standardisation.
- **Q2 2027 (months 10&ndash;12)**: stable 1.0 release, target 10,000 active users, expansion into Romania, Horizon Europe consortium submitted.

Each stage has a public sprint plan on GitHub Issues; each week of Sprint 0 (18&ndash;30 May) is documented as a runbook in the repository. There are no closed-door meetings.

## How you can contribute

For you, reading this:

- **Developers with Synapse, Element, Rust, Kotlin, or Swift experience**: see `docs/issues-to-create.md` — a few hundred tickets already sorted under `good-first-issue`, `help-wanted`, `crypto-review-needed`.
- **DPOs, GDPR / eEvidence / AI Act lawyers**: we need review for the DPIA and ROPA before the NLnet submission (deadline 30 May). Write to <legal@md-chat.eu>.
- **Moldovan companies looking for an internal E2EE workspace with integrated AI**: we run an early-access programme with 5&ndash;10 slots. Write to <oleg@megapromoting.com>.
- **Universities, institutions, NGOs in Moldova or the diaspora**: letters of support for the NLnet application and for future Sovereign Tech Fund applications. Write to <oleg@megapromoting.com>.
- **Journalists**: everything you need for a story is in the [press kit](https://md-chat.eu/press) or you can email <press@md-chat.eu> directly for a 30-minute interview in Romanian, Russian or English.
- **Translators RO &harr; RU &harr; EN &harr; UA**: we open the Weblate project in two weeks.

## A personal note

I have been in tech for almost 15 years. I have built products that worked, products that died, and I crossed two economic crises and a pandemic with a small team. I have never written a product that tries to be infrastructure for people who do not know me personally. MD-Chat is the first.

I am afraid I will fail. I am more afraid I will not try.

If there is a moment when a citizen of Moldova can build something at the level of Europe and for Europe, it is now. We are a candidate. Pavel Durov has shown us that "global" platforms are national when it comes to jurisdiction. The EU has shown us, through the AI Act + eEvidence + CRA + EUDI Wallet, the rules for the next decade.

We launch on 18 May. Readers are invited. The code is at [github.com/olegchetrean/md-chat](https://github.com/olegchetrean/md-chat). The site at [md-chat.eu](https://md-chat.eu). Discussion on [#md-chat:matrix.org](https://matrix.to/#/#md-chat:matrix.org).

Thank you for reading this far. See you in the issue tracker.

---

*Oleg Chetrean is the CEO of Mega Promoting SRL, a Moldova IT Park resident, and the founder of MD-Chat. This text is licensed CC-BY-SA 4.0 — you may republish with attribution.*
