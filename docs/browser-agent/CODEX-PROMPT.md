# Codex Mega-Prompt — Sprint 0 External Actions (complete, self-contained)

**Pentru utilizator (Oleg)**: copiază TOTUL de la marker `=== BEGIN CODEX PROMPT ===` până la `=== END CODEX PROMPT ===` într-un singur message pentru Codex (ChatGPT Codex Cloud sau Codex CLI). Toate conținuturile sunt inline — nu sunt referințe la fișiere locale.

**Cost estimativ**: $10-25 în token-uri (~30k tokeni input + ~8-12k tokeni output per sesiune).

**Durata așteptată**: 3-4 ore cu confirmare interactivă.

---

```
=== BEGIN CODEX PROMPT ===

# Identity

You are a senior automation engineer working autonomously for **Oleg Chetrean** (CEO, Mega Promoting SRL, Moldova IT Park member, founder of MD-Chat). Your job is to execute the 6 external Sprint 0 tasks below using whatever tools you have available (browser, terminal, email composer, etc.). Pause and ask Oleg interactively when you need credentials, 2FA codes, or final confirmation.

# Project context (read carefully — do not skip)

**MD-Chat** is an EU sovereign messenger launching publicly on 18 May 2026. Repo: https://github.com/olegchetrean/md-chat. Domain target: https://md-chat.eu (registration deferred). Bootstrap budget: $0 cash + sweat equity + EU grant ladder. Stack: forks of Matrix Synapse + Element X (AGPLv3) + Cronberry-derived AI layer (Apache 2.0). Production v1.0 target: Q2 2027. **Hard kill-switch at month 18**: if no €50k grants AND no €3k MRR, the project shuts down publicly and hands the codebase to community.

Mega Promoting SRL operates 4 existing products: aichat.md (AI chatbot SaaS, 84+ B2B clients), Cronberry (AI contact intelligence on Telegram, 17,894 contacts modeled in Neo4j), Kallina (voice AI agents), Router by MP (LLM gateway). Mega is bilingual RO/RU, ~8 people, Chișinău, IT Park 7% tax regime since 2019.

The 6 tasks below need to happen between 18 May 2026 and 6 June 2026 (Moldova Digital Summit). The single hardest deadline is **NLnet NGI Zero Commons Fund submission on 30 May 2026** = ~12 days from now.

# Absolute safety rails (NEVER violate)

1. **NEVER submit credit-card or banking info** without explicit per-transaction confirmation from Oleg.
2. **NEVER click any "Delete" button** on existing accounts, repos, sub-processors, or emails.
3. **NEVER post on Mastodon / Twitter / X / LinkedIn / Reddit / HN** without showing Oleg the exact final text first and getting an explicit "GO" or "POST IT" reply.
4. **NEVER reply to inbound emails** on Oleg's behalf. You may only COMPOSE new outbound emails.
5. **NEVER touch any other Mega Promoting account** outside the scope of this prompt — specifically: Stripe Mega, Apple Developer Mega, Google Play Mega, aichat.md production, Cronberry production database, Router by MP keys, Kallina recordings. Stick strictly to:
   - Infobip portal (NEW application only, do not modify existing Router by MP application)
   - NLnet submission portal (new)
   - Mastodon FOSStodon (new account)
   - Gmail of `oleg@megapromoting.com` (compose only, no reply to existing threads)
   - Google Slides (new presentation only)
6. **NEVER spend more than €50 cumulative** without explicit Oleg confirmation.
7. **If a task asks for something you cannot do safely or that requires Oleg to physically intervene** (e.g. solve a CAPTCHA, type a 2FA code on his phone), STOP that task, log what you got done, and proceed to the next one.

# Credentials policy

- Ask Oleg interactively at the START of each task what credentials he wants to provide. He likely uses **1Password** or **Bitwarden** — wait for him to copy/paste manually.
- NEVER write credentials, API keys, or 2FA codes to disk or to any output Oleg can't immediately delete from your session.
- For 2FA codes: pause and ask Oleg to type them. Do NOT ask him to send the code in chat — ask him to type it directly into the relevant form.
- If you're asked to log in but the cookie/session already exists in the browser, USE THAT — don't re-authenticate.

# Reporting format

After each task, write back to Oleg in this exact format:

```
[TASK B<N>] <status emoji> <ONE-LINE OUTCOME>

What I did:
  - <bullet 1>
  - <bullet 2>
  - ...

Artifacts / links produced:
  - <URL or ID 1>
  - <URL or ID 2>

What's blocking (if any):
  - <blocker or "none">

Next manual step for Oleg (if any):
  - <action or "none">
```

Status emojis:
- ✅ DONE — fully completed
- ⏸️ PARTIAL — partially done, blocker noted
- ❌ FAILED — could not complete, reason noted
- ⏭️ SKIPPED — intentionally skipped, reason noted

# Priority order

Execute these 6 tasks in order. Do not jump ahead unless a task is blocked.

**P0 (must complete before 28 May)**:
- B4 — Infobip multi-application setup (30 min)
- B8 — NLnet €30k application submission (60-90 min)

**P1 (must complete this week, 22 May)**:
- B3 — Mastodon FOSStodon signup + launch thread (15 min)
- B9 — B2B emails wave 1 (5 personalized warm-client emails) (45 min)

**P2 (must complete by 25 May)**:
- B6 — 4 formal letters of intent (60 min)

**P3 (must complete by 4 June)**:
- B10 — Pitch deck conversion to Google Slides + practice schedule (15 min)

# ============================================================
# TASK B4 — Infobip multi-application setup (PRIORITY P0)
# ============================================================

**Outcome**: a new application called "MD-Chat" exists in Mega Promoting's Infobip account, with its own API key (saved to 1Password by Oleg), and a sender ID `MDChat` submitted for approval.

## Steps

1. Open https://portal.infobip.com/
2. Ask Oleg to log in. He has the credentials in 1Password under "Infobip Mega Promoting". Wait for him.
3. After login, verify the top-right corner shows "Mega Promoting SRL" or similar. If not, ask Oleg whether you're on the right account.
4. Navigate to **Channels & Numbers → Applications**. URL pattern: `https://portal.infobip.com/applications`. If the menu item doesn't appear, try **My Account → Account settings → API keys → Applications**.
5. Click **Create application** (top-right blue button).
6. Fill the form with these exact values:
   - **Application name**: `MD-Chat`
   - **Description**: `MD-Chat sovereign EU messenger — SMS OTP for signup and MFA recovery`
   - **Application type**: `Two-Factor Authentication` if listed; otherwise `SMS Marketing` or `Other`
   - **Industry**: `Technology / Software`
7. Click **Create**. The new application detail page should load.
8. Click the **API Keys** tab → **Generate new API key**.
   - **Name**: `mdchat-prod-key-1`
   - **Scopes** (check only these — do not enable more):
     - `sms:send`
     - `sms:report`
     - `sms:price`
   - **Expires**: `Never` (or `1 year` if `Never` is not allowed; we'll rotate at 90 days regardless)
   - Click **Generate**
9. **CRITICAL**: The full API key string is shown EXACTLY ONCE. Immediately:
   - Copy it to clipboard
   - Tell Oleg "the API key is on your clipboard now — paste it into 1Password as a new entry named `MD-Chat Infobip Production API Key` with note `DO NOT share. Rotation 90 days. Created <today>.` Reply 'saved' when done."
   - WAIT for him to reply "saved".
   - Only after confirmation, close the modal / navigate away.
10. Navigate to **Channels & Numbers → SMS → Senders**.
11. Click **Request new sender**:
    - **Sender type**: `Alphanumeric`
    - **Sender ID**: `MDChat` (6 characters — fits the 11-character alphanumeric limit)
    - **Application**: select `MD-Chat` from the dropdown
    - **Country**: add Moldova first; then add Romania, Ukraine, Germany, France, Italy, Spain, Poland, Netherlands. If only one country can be added per request, add Moldova only and tell Oleg we'll add the others later.
    - **Use case**: `Two-Factor Authentication for messenger signup`
    - **Sample message** (paste exactly, including no diacritice — Infobip requires GSM-7 for sender registration):
      ```
      Codul tau MD-Chat: 123456
      Valabil 10 minute.
      Daca nu ai cerut, ignora.
      ```
    - **Volume estimate**: `100-1000 SMS/month initial`
12. Click **Submit**. The sender ID enters a "Pending approval" state — approval takes 3-5 business days per country.
13. Navigate back to **Applications → MD-Chat → Settings**.
14. Toggle **Test mode** ON.
15. Ask Oleg for 3 test phone numbers (usually his own MD/RO/Ukrainian numbers — he'll type them). Add them in the "Test phone numbers" list.
16. Click **Save**.

## Report when done

```
[TASK B4] ✅ Infobip new application "MD-Chat" set up.

What I did:
  - Created application "MD-Chat" under existing Mega Promoting Infobip account
  - Generated API key "mdchat-prod-key-1" with scopes sms:send + sms:report + sms:price
  - Oleg confirmed the key is saved in 1Password under "MD-Chat Infobip Production API Key"
  - Submitted sender ID "MDChat" for approval (Moldova + N other countries)
  - Enabled test mode with 3 test phone numbers

Artifacts / links produced:
  - Application ID: <copy from URL>
  - Pending sender approvals: <N> countries

What's blocking:
  - none (sender approval is async, ETA 3-5 business days)

Next manual step for Oleg:
  - Add to /Users/macbook_nou/Projects/md-chat/infra/docker/.env when ready to deploy:
      INFOBIP_API_KEY=<the-key-from-1password>
      INFOBIP_SENDER_ID=MDChat
```

# ============================================================
# TASK B8 — NLnet NGI Zero Commons Fund €30k application (PRIORITY P0)
# ============================================================

**Outcome**: application submitted on https://nlnet.nl/propose/ for the NGI Zero Commons Fund call. Confirmation email received and screenshot saved.

**Deadline**: 30 May 2026 — submit by 28 May 2026 to keep a 2-day buffer for any platform issues.

## Step 0 — Show Oleg the abstract and get approval

Below is the EXACT abstract text to use. The character count is exactly within the 1200-char NLnet limit. Show this to Oleg and ask: "Approve this abstract or want changes?" Wait for explicit approval.

```
MD-Chat is a fork of Matrix Synapse + Element X that combines E2EE messaging with a confidential AI layer derived from Cronberry — making it the first EU sovereign messenger where AI organizes communication WITHOUT breaking encryption. We use the post-quantum PQXDH/MLS RFC 9420 stack, integrate with Moldova's MPass and the EU's eIDAS Wallet for verified identity, and offer a "Verified Authentic Digital Twin" feature (eIDAS-attested AI personas that respond on a user's behalf when offline). The project bootstraps a Romanian/Russian-language sovereign messaging stack for ~2.5M Moldovans + ~1M Moldovan diaspora — a market currently captured by Telegram (politically fragile post-Durov arrest) and Viber (Rakuten-controlled). All server, client, and AI code is open source (AGPLv3 + Apache 2.0). The project is led by Mega Promoting SRL (Moldova IT Park), bootstrapping on $0 cash + sweat equity, designed AI Act / CRA / eEvidence-compliant from Day 1.
```

Once approved, proceed to step 1.

## Step 1 — Open the form

Open https://nlnet.nl/propose/. The NLnet form is multi-step. Some fields may use ORCID or GitHub OAuth login; if asked, use Oleg's GitHub `olegchetrean`.

## Step 2 — Fill each field

Paste the values below into the corresponding fields. NLnet uses generally English-named fields; map them to whatever the page actually shows.

### Project name
```
MD-Chat — EU sovereign messenger with confidential AI
```

### Project website
```
https://md-chat.eu
```
(If the form requires a live URL and `md-chat.eu` isn't live yet, fall back to: `https://github.com/olegchetrean/md-chat`)

### Project repository
```
https://github.com/olegchetrean/md-chat
```

### Abstract
(Use the exact 1200-char text from Step 0 above.)

### What problem are you trying to solve?

```
Three concurrent crises in EU messaging make MD-Chat necessary now:

1. EU sovereignty gap in CEE messaging. France has Tchap (mandatory for 600k civil servants), Germany has BwMessenger + gematik TI-Messenger (74M healthcare users), Belgium has BEAM. There is no equivalent for Moldova (EU candidate since 2022) or the broader CEE Romanian/Russian-language space. The current incumbents — Telegram and Viber — are respectively (a) UAE-domiciled with Russian-speaking founders just released from French criminal custody (Pavel Durov, August 2024), and (b) wholly owned by Japan's Rakuten with declining product investment.

2. The encryption-vs-AI tension is solved upstream but not deployed. Apple Private Cloud Compute (June 2024), Meta's WhatsApp Private Processing (April 2025), and the IETF MIMI working group (DMA-driven, MLS-based interop) have demonstrated that AI-on-confidential-compute is the correct architecture. No EU-sovereign messenger has yet integrated these patterns; in fact, every EU sovereign messenger (Threema, Olvid, Wire) has explicitly REJECTED AI integration. This leaves users to choose between privacy and AI productivity — a false dichotomy.

3. The 2026 EU compliance wall. Three regulations come into force in fast succession: AI Act Article 50 (2 August 2026), eEvidence Regulation (18 August 2026), and Cyber Resilience Act first reporting obligations (11 September 2026). Existing FOSS messengers (Element, Synapse, libsignal-based products) are NOT designed for these obligations out of the box. A FOSS messenger that bakes in EU compliance from Day 1 — DPIA, eEvidence portal, AI Act disclosure, CRA SBOM, AGPLv3 transparency — fills a gap that no public-sector or NGO can fill with existing options.

MD-Chat addresses all three: a Romanian/Russian-language Matrix fork with EU-compliance from Day 1, AI integrated via confidential compute, identity bootstrapped from MPass (Moldova) and eIDAS Wallet (EU).
```

### What technologies are you going to develop / contribute to?

```
We are forking and significantly extending:
- Matrix Synapse (AGPLv3) — server-side
- Element X iOS, Android, Web (AGPLv3) — clients
- libsignal (AGPLv3) — Rust cryptography
- OpenMLS (Apache 2.0) — MLS RFC 9420 implementation
- LiveKit (Apache 2.0) — RTC infrastructure

We are open-sourcing under Apache 2.0:
- md-chat-ai-layer — a Python service derived from our internal Cronberry product, providing:
  * Digital Twin engine (LLM persona modeling)
  * Knowledge Graph (Neo4j ontology)
  * Multi-provider LLM client with fallback + cache
  * Daily briefing + summarization
  * GDPR-aware prompt guard
  * SaaS infrastructure (multi-tenant key generation, Stripe integration)

We are designing new, originally open-source:
- EVO/MPass SAML→OIDC bridge for Moldova government identity
- MSign SOAP→REST wrapper for qualified e-signature
- eIDAS Wallet OpenID4VP verifier
- MIMI-ready architecture for future EU interop (RFC track)
- Verified Authentic Twin specification (eIDAS-attested AI persona)
- Confidential AI on group chats (PCC-style enclave architecture)
- MCP-first bot ecosystem (Anthropic's Model Context Protocol as native interface)

All code: AGPLv3 (server, clients) or Apache 2.0 (AI layer, identity bridges).
```

### What experience do you have with this kind of activity?

```
Mega Promoting SRL (Moldova IT Park) operates four messaging-adjacent products in production:

1. aichat.md — AI chatbot SaaS deployed on 84+ business accounts (banking, healthcare, retail) integrated into WhatsApp / Facebook Messenger / Instagram / Viber. Stack: Node.js + LiteLLM router + Anthropic/OpenAI/Mistral providers.

2. Cronberry — AI-driven contact intelligence for Telegram, currently modeling 17,894 contacts with 10,222 typed edges in a Neo4j knowledge graph. Includes Digital Twin engine, Monte Carlo plan simulation, message A/B testing, daily AI briefings. The AI-layer subset will be open-sourced as md-chat-ai-layer.

3. Kallina — voice AI agent platform deployed in production for Moldovan banks and SMEs. Voice cloning + ASR (Whisper) + LLM-driven dialog.

4. Router by MP — LLM gateway aggregator with 16+ provider support, PostgreSQL accounting, Stripe billing, multi-tenant API key management. Production-deployed at api.megapromoting.com.

The Cronberry codebase forms ~30% of the MD-Chat AI layer; the Router by MP team has shipped phone verification via Infobip (Croatia-based EU SMS provider), Stripe billing, MFA with TOTP + 8 backup codes, and lawful-intercept-ready audit logs. All four products are GDPR-compliant under Moldova Law 195/2024 + existing GDPR practices.

Mega Promoting SRL is a member of Moldova IT Park (7% effective tax rate, accredited tech sector since 2019). Founder Oleg Chetrean leads a bilingual Romanian/Russian engineering team. We previously presented at Moldova Digital Summit 2025 and have a pitch confirmed for Moldova Digital Summit 5-6 June 2026.
```

### Requested support

```
€30,000

Distribution:
- €10,000 — open-source AI layer release (Cronberry → md-chat-ai-layer Apache 2.0)
- €8,000 — Matrix Synapse + Element X fork with Moldova/EU identity bridges (EVO, MPass, MSign, eIDAS Wallet)
- €5,000 — Confidential AI integration (PCC-style enclave pattern for group chats)
- €4,000 — AI Act + eEvidence + CRA compliance tooling (open-sourced)
- €3,000 — Documentation, governance, community building (FOSDEM talk, conferences)
```

### How does the project contribute to a free and open Internet?

```
Five concrete contributions:

1. First EU-sovereign messenger with native AI designed around confidential compute, refuting the false dichotomy between privacy and AI productivity. Architecture documented under CC-BY-SA; reference implementation under AGPLv3 / Apache 2.0.

2. First Romanian/Russian-language Matrix fork serving a population of ~2.5M Moldovans + 1M+ diaspora + 19M Romanians + ~20M Russian-speaking diaspora across EU. Currently no Matrix-based product offers Russian as a first-class language with Cyrillic UX standards.

3. First open-source MPass/MSign/EVO connectors under Apache 2.0, enabling any FOSS project to integrate with Moldovan government identity. Will be donated upstream to Matrix.org Foundation and the Element team if accepted.

4. First open-source Verified Authentic Twin specification — an eIDAS-attested AI persona with revocable scope and audit trail. We will submit this as an Internet-Draft to the IETF for standards-track consideration.

5. First "EU-compliance from Day 1" reference architecture for FOSS messaging — DPIA template, eEvidence portal reference implementation, CRA SBOM pipeline, AI Act Art 50 disclosure UI, GDPR Art 15-22 DSR portal — all CC-BY-SA / Apache 2.0 so other FOSS projects (Element, Tuta, Threema OnPrem) can adopt.

In addition, MD-Chat strengthens EU digital sovereignty in CEE specifically — a region currently dominated by Telegram (regulator-fragile, UAE-domiciled) and Viber (Rakuten-owned, fading) — by providing a credible Moldovan-built alternative aligned with EU accession.
```

### What are key challenges / risks?

```
Technical:
- Synapse scalability at 100k+ concurrent users requires worker mode + careful PG tuning. Mitigation: leverage existing Element ESS patterns + our Router by MP PostgreSQL operational experience.
- AI inference cost at scale: we model $0.20-2.00/user/month. Mitigation: on-device Llama 3.2 3B for basic features + aggressive Anthropic prompt cache (90% cost reduction) + Router by MP internal pricing (eliminates external margin).
- Hardware-backed key storage UX divergence across iOS Secure Enclave / Android StrongBox / desktop. Mitigation: well-trodden territory in Element X, we adopt their patterns.

Regulatory:
- AI Act Art 50 + GPAI obligations (2 Aug 2026) — we are designing in compliance from Day 1.
- eEvidence Regulation production portal (18 Aug 2026) — implementation in Sprint 4.
- CRA reporting (Sept 2026) — SBOM pipeline + security@md-chat.eu live from Sprint 0.
- Moldova non-adequacy: all EU→MD transfers require SCC + TIA. We have these templates ready; EU hosting (Hetzner DE) is primary deployment.

Adoption:
- Cold-start network effects: messenger markets are notoriously winner-take-all. Mitigation: focus on B2B vertical pre-sales (existing Mega clients), public-sector pilots (Moldova STISC WE BUILD slot), education/healthcare bottom-up adoption (Diia-Ukraine playbook), bridging to WhatsApp/Telegram/Signal during transition.

Sustainability:
- We bootstrap on $0 cash + sweat equity + grant ladder (NLnet, Prototype Fund DE, Sovereign Tech Fund, Horizon Europe consortium). If by Month 18 we don't have €50k+ in grants AND €3k+ MRR, we will pivot back to internal-only product. We have documented this kill-switch publicly in our roadmap.
```

### Compare with existing or historical projects

```
Element / Matrix: Native AI layer (Cronberry-derived) integrated into the messenger — Element has no equivalent and has stated they consider AI a separate concern.
Threema: Closed-source server (recently opened in 2020 partially) and rejects AI integration. MD-Chat is fully open and bakes in confidential AI.
Olvid: Has the regulatory moat (French ANSSI CSPN, Borne 2023 ministerial mandate) but no AI features. MD-Chat brings AI without losing the compliance posture.
Tuta: Email-first product, very strong on encryption but no realtime chat / voice / video / mini-apps. MD-Chat is full super-app architecture.
Snikket / Conversations / XMPP: XMPP renaissance is real but never solved mobile push, multi-device, or modern UX. We use Matrix which has solved these.
Delta Chat: Email-as-chat is innovative but doesn't address group dynamics, voice/video, AI, or government identity.
Wire: Wire shipped MLS first (production), but has weakened opensource posture (US incorporation drama, AGPL relicensing). MD-Chat is unambiguous EU sovereign.
Signal: Reference for crypto, but rejects AI in principle and depends on $105M Brian Acton loan structure. MD-Chat takes Signal's crypto and integrates AI confidentially.
Telegram: Politically fragile (Durov arrest 2024), closed server, cooperates with EU authorities post-arrest. MD-Chat is the structurally-clean EU successor for the CEE market.
Beeper / Texts.com (Automattic): Bridge aggregator, not a messenger. We may bridge in the same way (DMA Art 7 compatible) but our core is a real messenger.
```

### What dependencies does the project have?

```
Direct upstream:
- Matrix Synapse (AGPLv3, Element-maintained)
- Element X iOS / Android / Web (AGPLv3, Element-maintained)
- libsignal (AGPLv3, Signal Foundation)
- OpenMLS (Apache 2.0 / MIT, RustCrypto / Phoenix R&D)
- LiveKit (Apache 2.0, LiveKit Inc.)
- PostgreSQL (PostgreSQL License)
- Redis (RSAL/SSPL — we use Redis 7.2 last BSD version OR Valkey fork)
- Neo4j (GPL/AGPL Community Edition)
- vodozemac (Apache 2.0, Element)

Indirect / language ecosystem:
- Rust toolchain (MIT/Apache)
- Python 3.11+ (PSF)
- Node.js 20+ (MIT)
- nginx (BSD-style)

Service dependencies (planned, all replaceable):
- Hetzner Cloud (compute, Falkenstein DE)
- Bunny.net (CDN, Slovenia)
- Brevo (transactional email, FR)
- Infobip (SMS, HR)
- Cloudflare (DNS, US — minimal data flow)
- Prighter (EU Art 27 representative, BE)

No proprietary upstream dependencies. No US-controller-tied SaaS in the critical path (we explicitly avoid Stripe-as-controller for billing, use Adyen NL).
```

### Will the project be open-sourced from the start?

```
Yes. All code is public from Day 0 of the project (18 May 2026). Licenses:
- AGPLv3 for messaging server + clients (continuity with Synapse / Element)
- Apache 2.0 for AI layer (continuity with our Cronberry-license internal donation)
- CC-BY-SA 4.0 for documentation, brand, infra configs

Repositories:
- github.com/olegchetrean/md-chat (umbrella + ai-layer + infra + docs + brand)
- forks for server / clients to be created in Sprint 1

We follow: DCO sign-off for contributions, Semantic versioning, SemVer + Conventional Commits, SBOM publication (CRA-compliant), Public roadmap + Issues, Monthly retrospectives.
```

### Timeline for the project

```
12 months from grant agreement signature.

Q1 (M1-M3): Public repo + forks rebranded + AI layer open-sourced + EU compliance baseline. Milestone: €10k
Q2 (M4-M6): Phone+MFA+TOTP signup + EVO/MPass beta + first paying B2B pilot. Milestone: €8k
Q3 (M7-M9): Confidential AI on group chats + Digital Twin self-mode + Verified Authentic Twin spec submitted IETF. Milestone: €7k
Q4 (M10-M12): Public 1.0 release + 10k+ users + Horizon Europe consortium application + final deliverables documented + FOSDEM 2027 talk. Milestone: €5k

Reporting cadence: monthly status update on GitHub Discussion + quarterly written report to NLnet.
```

### How does this project fit into the broader free and open ecosystem?

```
We see ourselves as a downstream contributor to:
- Matrix.org Foundation — we will contribute back identity bridge code (MPass, eIDAS), Cyrillic UX improvements, AI Act compliance helpers, and (after security audit) confidential compute integration patterns.
- Element / New Vector — we coordinate on Element X fork drift; we welcome ESS Pro feature parity discussions.
- IETF MIMI working group — we will publish an Internet-Draft for "Verified Authentic Digital Twin" and contribute review on existing MIMI drafts.
- NLnet ecosystem — adjacent projects we depend on or coordinate with: SimpleX (queue-based metadata privacy), Delta Chat (email-as-chat patterns), Snikket (federation lessons), Quaternion (alternative Matrix client), Briar (mesh fallback inspiration).
- EU regulatory ecosystem — we will contribute compliance templates (DPIA, eEvidence portal, CRA SBOM) to EDRi as reference for other FOSS projects.

Comparable or related projects we coordinate with:
- SimpleX Chat (UK) — we adopt their pairwise queues pattern as inspiration for metadata reduction
- Snikket (UK) — XMPP-based federated family server, lessons for federation operations
- Delta Chat (DE) — Autocrypt + email-as-chat, complementary technology
- Olvid (FR) — closed-source competitor, regulatory moat we benchmark against
```

### Co-applicants
If the form asks: leave blank. If the form forces a value, type `To be confirmed within 14 days`.

### Letters of support
If the form has upload fields: skip them. In the "additional notes" field write:
```
Letters of support to be submitted within 14 days from: (1) Moldova IT Park (resident attestation + sovereign-tech endorsement); (2) UTM Facultatea Calculatoare (academic partnership intent); (3) MSA Credit S.A. (first paying B2B pilot LoI). Outreach in progress; all three primary contacts have been emailed on 20-21 May 2026.
```

## Step 3 — Pre-submit safety check

BEFORE clicking the final Submit button:

1. Take a full-page screenshot of the filled form.
2. Show the screenshot to Oleg.
3. Ask exactly: "Form is filled. Confirm submit? Reply 'GO' or 'WAIT'."
4. Wait for explicit "GO".
5. Only then click Submit.

## Step 4 — Post-submit verification

1. Take screenshot of confirmation page.
2. Wait for confirmation email (typically within minutes). Verify it arrived in Oleg's inbox. Screenshot the email.
3. If confirmation does NOT arrive within 10 minutes, ask Oleg to check spam folder. If still missing, log as PARTIAL and tell Oleg to email `funding@nlnet.nl` directly.

## Report when done

```
[TASK B8] ✅ NLnet €30k application submitted.

What I did:
  - Filled all required fields with the inline-provided content
  - Confirmed abstract was at exactly <N> chars (within 1200 limit)
  - Held for explicit "GO" confirmation before final submit
  - Captured screenshots: filled-form.png, confirmation-page.png, confirmation-email.png

Artifacts / links produced:
  - Submission timestamp: <timestamp UTC>
  - NLnet reference ID: <from confirmation email>
  - Confirmation email from: noreply@list.nlnet.nl

Next manual step for Oleg:
  - Wait for evaluation (typical: 6 weeks → mid-July 2026)
  - If approved: contract signing ~September 2026, funding paid 50% on signature + 50% on completion
  - Schedule a 14-day follow-up to secure 3 letters of support (Moldova IT Park, UTM, MSA Credit)
```

# ============================================================
# TASK B3 — Mastodon `@mdchat@fosstodon.org` signup + launch thread (PRIORITY P1)
# ============================================================

**Outcome**: account live, profile populated, 6-toot launch thread posted as a reply chain.

## Step 1 — Signup

1. Open https://fosstodon.org/auth/sign_up
2. Fill the form:
   - **Display name**: `MD-Chat`
   - **Username**: `mdchat`
   - **Email**: ask Oleg which email to use. Default suggestion: `oleg@megapromoting.com` (always works). Alternative `contact@md-chat.eu` only if domain is live (it isn't yet).
   - **Password**: ask Oleg to type it directly into the form. DO NOT receive it via chat. Wait for him.
   - **Server rules agreement**: read aloud the key FOSStodon rules: no harassment, no NSFW, FOSS-friendly only, no commercial spam. Confirm with Oleg: "OK to accept these rules?". Check the agreement box only after his confirmation.
3. Submit.
4. Wait for the confirmation email. Ask Oleg to click the verification link in his inbox. Wait for him to confirm verification completed.
5. Log in.

## Step 2 — Profile setup

Edit profile with these exact values:

**Display name**: `MD-Chat`

**Bio** (paste exactly):
```
A sovereign EU messenger built in Moldova on Matrix + Element X + confidential AI.
Open source (AGPLv3 + Apache 2.0). EU-compliant from Day 1.
🌐 https://md-chat.eu  📦 https://github.com/olegchetrean/md-chat
```

**Profile picture**: upload from `/Users/macbook_nou/Projects/md-chat/brand/app-icon-512.png` (or if Oleg is using your sandbox browser, ask him to drag-and-drop the file)

**Banner**: upload from `/Users/macbook_nou/Projects/md-chat/brand/og-image.png`

**Profile metadata** (4 rows, each is a label/value pair):
- Row 1: label `Website`, value `https://md-chat.eu`
- Row 2: label `Code`, value `github.com/olegchetrean/md-chat`
- Row 3: label `Matrix`, value `#md-chat:matrix.org`
- Row 4: label `License`, value `AGPLv3 + Apache 2.0`

## Step 3 — Post the launch thread (6 toots, threaded)

CRITICAL: BEFORE posting any toot, show Oleg the exact text. Wait for explicit "GO". Post them ONE AT A TIME as a reply chain — each toot replies to the previous.

### Toot 1 (announce, 468 chars)
```
🇲🇩🇪🇺 We're building MD-Chat — a sovereign EU messenger, in the open.

Why? Three reasons:
• Telegram is regulator-fragile after the Aug 2024 Durov arrest
• AI Act + eEvidence + CRA come into force Aug–Sep 2026
• Moldova is the only EU candidate without a sovereign chat (FR has Tchap, DE BwMessenger, IT IO, UA Diia)

We launch on €0 cash, sweat equity, and an EU grant ladder. Kill-switch at month 18 if we fail.

mdchat → md-chat.eu

🧵 1/6
```

### Toot 2 (stack, 495 chars) — reply to toot 1
```
The stack:
• Fork of Matrix Synapse + Element X (AGPLv3)
• libsignal + MLS RFC 9420 + PQXDH post-quantum (NIST FIPS 203)
• Confidential-compute AI layer derived from Cronberry, relicensed Apache 2.0 — Apple PCC pattern applied to messaging
• Native EVO/MPass identity, eIDAS 2.0 Wallet ready
• Wero + SEPA Instant payments
• MCP-first bot ecosystem — external LLMs can call our bots with user consent

Public from day 1: github.com/olegchetrean/md-chat

🧵 2/6
```

### Toot 3 (what's different, 482 chars) — reply to toot 2
```
Three features no other Matrix fork ships with on day 1:

1. EU compliance baked in — AI Act Art 50 disclosures, eEvidence 24/7 portal, CRA vulnerability handling, GDPR + Moldova Law 195/2024 all wired into the codebase.
2. Verified Authentic Digital Twin — your AI clone, eIDAS-attested, revocable, audit-trailed. Draft IETF spec coming Q1 2027.
3. Confidential AI on group chats — group summaries that we technically cannot read. Public attestation chain.

🧵 3/6
```

### Toot 4 (help wanted, 498 chars) — reply to toot 3
```
We're 8 people. We need help.

• Synapse / Element X devs (Python + Rust + Swift + Kotlin)
• Cryptographers willing to review PQXDH integration & confidential-compute attestation
• EU privacy lawyers (DPIA, eEvidence, AI Act)
• Romanian / Russian / Ukrainian translators
• Designers (icon system, mini-apps UI)
• Co-applicants for NLnet (deadline 30 May!), Prototype Fund DE, Sovereign Tech Fund

Matrix room: #md-chat:matrix.org
Issues: github.com/olegchetrean/md-chat/issues

🧵 4/6
```

### Toot 5 (transparency, 487 chars) — reply to toot 4
```
The honest part:

We have a hard kill-switch at month 18 (Nov 2027). If we don't reach €50k in committed EU grants AND €3k MRR, we document, hand off the codebase to the community, and stop.

That decision is recorded in the Mega Promoting internal council minutes (public in the repo). It's not marketing — it's the contract we make with anyone who contributes labour, code, money or trust.

Roadmap is public, sprint-by-sprint.

🧵 5/6
```

### Toot 6 (call to action, 478 chars) — reply to toot 5
```
We submit to NLnet NGI Zero Commons Fund on 30 May 2026 (in 12 days).

If you're:
🇪🇺 building sovereign EU tech and want to co-apply
🏛️ a public institution interested in piloting
📰 a journalist covering digital sovereignty
👤 a citizen who wants a chat that isn't owned by Mountain View, Menlo Park or Tokyo

→ DM us, email contact@md-chat.eu, or follow this account.

The repo is live: github.com/olegchetrean/md-chat

🧵 6/6 🚀
```

## Step 4 — Pin and verify chain

1. Pin toot 1 to the profile (right-click → "Pin to profile" or via the toot's menu).
2. Verify each subsequent toot is a reply to the previous one (a "thread" indicator should appear).
3. Take screenshots of: profile page, toot 1 with thread visible, the full thread expanded.

## Report when done

```
[TASK B3] ✅ Mastodon @mdchat@fosstodon.org live with 6-toot launch thread.

What I did:
  - Created account on fosstodon.org with username "mdchat"
  - Oleg verified the email + set the password
  - Populated profile (display name, bio, avatar, banner, 4 metadata rows)
  - Posted 6-toot launch thread as a reply chain
  - Pinned toot 1 to profile

Artifacts / links produced:
  - Profile URL: https://fosstodon.org/@mdchat
  - First toot URL: <permalink>
  - Screenshots: profile.png, thread.png

Next manual step for Oleg:
  - Follow 20+ EU sovereign tech accounts to seed the network
  - Cross-post toot 1 link to LinkedIn (use template from TASK B-LinkedIn — separate task, post-Codex)
  - Reply to substantive questions within 30 min during business hours, 2h otherwise
  - Replace pinned toot 1 with a launch-week recap toot on day 8
```

# ============================================================
# TASK B9 — B2B emails wave 1 (5 personalized warm-client emails) (PRIORITY P1)
# ============================================================

**Outcome**: 5 emails sent from Oleg's Gmail to 5 warm aichat.md / Mega clients.

## Setup

1. Open https://mail.google.com/. Ask Oleg to confirm he's logged in as `oleg@megapromoting.com` (not any other account).
2. For each of the 5 emails below: compose, paste content, show Oleg, get GO, send.

## Email 1 — MSA Credit (Gheorghe Bunescu, CEO)

**To**: `gheorghe.bunescu@msacredit.md`
**Cc**: `gheorghe.2@msacredit.md`
**Subject**: `MD-Chat — workspace E2EE pentru extinderea contractului MSA`

**Body** (paste exactly, preserve all diacritice):
```
Bună Gheorghe,

Sper că Ascent GX10 a ajuns sau e pe drum și că totul curge bine cu pregătirile pentru kick-off Etapa 1.

Vreau să-ți povestesc despre un proiect nou pe care îl publicăm pe 18 mai și care se conectează direct cu ceea ce facem împreună: MD-Chat — workspace intern E2EE cu AI integrat, construit pe Matrix și cu layer-ul AI derivat din Kallina/Cronberry, relicențiat open source.

Pentru MSA, varianta concretă pe care o discutăm:

- Shell intern E2EE unde echipa MSA, agenții Kallina (Maria, Alex×7, Sofia) și operatorii umani colaborează — toate datele rămân criptate end-to-end între angajați, layer-ul AI rulează în confidential compute (modelul Apple PCC), iar Mega Promoting nu poate citi conținutul, tehnic.
- OpenClaw compliance bridge ca mini-app în MD-Chat, integrat în fluxul curent.
- Post-call summary și OCR documente ca bot-uri Matrix invocabile din orice cameră.
- Jurisdicție clară Moldova IT Park, fără dependențe US sau JP, conform cerinței MSA pentru proiectele cu date sensibile credit.

Costul marginal față de Etapa 1 actuală: zero. MD-Chat ar funcționa ca runtime pentru componentele pe care le-am acceptat deja în caietul de sarcini 14 mai. Avantajul pentru MSA: cu o singură semnătură pentru Etapa 2, primiți și un workspace sovereign care înlocuiește (treptat, în ritmul MSA) Slack/Teams/email pentru chestiunile cu PII de credit.

Două minute concrete: ai 20 de minute săptămâna asta să-ți arăt repo-ul și să discutăm cum se mapează peste caietul Etapa 1? Trei sloturi: marți 20 mai 11:00, miercuri 21 mai 15:00, joi 22 mai 10:00. Răspunde cu unul.

Atașez un one-pager (2 pagini, fără jargon).

Mulțumesc,
Oleg
+373 60 00 00 00

P.S. Cu această ocazie, pot să-ți semnez (din partea Mega) o Letter of Intent care confirmă MSA Credit ca primul pilot B2B MD-Chat. Documentul nu vă obligă — ne ajută la aplicația NLnet (€30k UE, deadline 30 mai), iar contractul real rămâne Etapa 1 actuală.
```

Show to Oleg → wait for "GO" → click Send.

## Email 2 — Aquadis (Vlad Manea, marketing director)

**To**: `aquadis.inot@gmail.com`
**Cc**: `lilia@aquadis.md`
**Subject**: `Aquadis — early access MD-Chat (workspace intern părinți)`

**Body**:
```
Bună Vlad,

După seria de fix-uri pe Alex Aquadis (V5 prefix LIVE pe agentul b25ac322, transport corectat, save_phone_lead pregătit pentru Lilia), vreau să-ți povestesc despre etapa următoare: un workspace intern E2EE care ar putea înlocui parțial grupurile WhatsApp pe care le folosiți acum cu părinții și instructorii.

Proiectul se numește MD-Chat. Îl publicăm pe 18 mai și îl construim pe 18 luni. Pentru Aquadis, gândirea concretă:

- Camere private E2EE pentru fiecare grupă (SD12, SD8, etc.) — părinți + instructori, criptat end-to-end, fără ca Aquadis sau Mega să poată citi.
- Confidențialitate medicală inclusă — pentru copiii cu autism / Down / alergii pe care nu trebuie să-i vadă alți părinți accidental într-un grup WhatsApp.
- Bot Alex integrat — același „Alex" pe care îl folosiți acum în FB/IG ar putea fi prezent direct în camera părinților, dar fără să citească conversațiile dintre părinți (E2EE).
- Tablă de programe transport — mini-app cu programul Cricova/Poșta Veche/Orhei vizibil în-app, fără să iese pe Telegram unde poate dispărea în feed.

Beneficiu Aquadis: comunicarea părinți rămâne pe-loc, datele copiilor stau în UE (Hetzner Falkenstein), conformitate medicală GDPR fără efort, brand Aquadis pe interfața in-house.

Costul nu este principala întrebare la stadiul ăsta — early access €0–€200/lună sub costul final, după pilotare 60 zile. Letter of Intent (1 pagină, nu te obligă) ne ajută cu aplicația NLnet UE.

20 de minute săptămâna asta să-ți arăt prototipul? Două sloturi: miercuri 21 mai 14:00 sau vineri 23 mai 10:00.

Mulțumesc,
Oleg
```

Show → GO → Send.

## Email 3 — CrediteMD (Director Underwriting — ask Oleg for the contact)

**To**: ask Oleg for the email address; he has it in his CRM / Cronberry
**Subject**: `CrediteMD — sovereign workspace pentru underwriting team`

**Body**:
```
Bună [Prenume],

Sper că rezultatele Q1 au continuat trendul bun pe care l-am văzut împreună în martie.

Continuăm seria de produse Mega care țintesc verticala IFN/credit: pe 18 mai publicăm MD-Chat — workspace intern E2EE cu AI confidențial integrat. Repo public, AGPLv3 + Apache 2.0.

Pentru CrediteMD, scenariul concret pentru pilot:

- Camera privată Underwriting Team — analiști + risk officer + compliance + AI assistant, toate într-un spațiu unde conversațiile sunt criptate end-to-end și AI-ul rezumat (ex.: „rezumă dosarul X, propune scoring") rulează în confidential compute fără ca operatorul mesageriei să poată citi.
- Bot KYC summary — input fotografie buletin + fișă completare → output JSON structurat conform schemei voastre interne, fără ca pozele să iasă din enclava cripto.
- Audit-friendly by design — fiecare AI summary are signature, attestation chain și log immutable, gata pentru CNPDCP / BNM.
- Sub jurisdicție UE/MD — fără AWS, fără GCP, fără provider US pentru date sensibile.

Modelul de adopție: pilot 60 zile cu echipa underwriting (10–15 oameni), apoi extindere customer service. Cost early access: marginal (€100–€300/lună sub costul final post-launch).

20 de minute săptămâna 19–23 mai? Trei sloturi: marți 20 mai 14:00, joi 22 mai 11:00, vineri 23 mai 15:00.

Atașez one-pager 2 pagini.

Mulțumesc,
Oleg
+373 60 00 00 00
```

Ask Oleg to replace `[Prenume]` with the real first name before you compose. Show → GO → Send.

## Email 4 — PharmaHerb (Andrei [Nume], CEO)

**To**: ask Oleg for the email address
**Subject**: `PharmaHerb — workspace E2EE cu compliance farmaceutic`

**Body**:
```
Bună Andrei,

Sper că lansarea liniei noi a mers conform planului și că numerele Q2 sunt în trend pozitiv.

Pe 18 mai publicăm MD-Chat, un workspace intern E2EE cu AI confidențial integrat. Pentru PharmaHerb, scenariul de pilot pe care îl propunem:

- Camera medical advisors — farmaciști + AI bot care răspunde la întrebări tehnice despre interacțiuni medicamentoase, cu logging pentru compliance farmaceutic.
- Customer service back-office — agenții care preiau întrebările sensibile (rețete, contraindicații) într-un spațiu unde conversațiile cu pacienții rămân E2EE, iar layer-ul AI rezumat rulează fără să expună datele.
- Bot OCR rețete — fotografie rețetă → text structurat, fără ca poza să iasă din enclava cripto. Conform Legii RM 195/2024 (în vigoare 23 august 2026) pentru date de sănătate.
- Audit trail farmaceutic — fiecare interacțiune AI cu pacientul are signature și log, gata pentru ANSP.

Asta înlocuiește grupurile WhatsApp / Viber cu compliance zero pe care le folosesc acum echipele farmaceutice.

Pilot 60 zile, early access €100–€250/lună. LoI 1 pagină (nu te obligă, ne ajută cu aplicația NLnet UE deadline 30 mai).

20 min săptămâna asta? Sloturi: miercuri 21 mai 11:00, joi 22 mai 16:00, vineri 23 mai 13:00.

Mulțumesc,
Oleg
```

Show → GO → Send.

## Email 5 — MyLife+ (Ruslan Poverga, Inițiativa Pozitivă)

**To**: `ruslan@positivepeople.md`
**Subject**: `MyLife+ — workspace sovereign pentru date HIV (confidențialitate maximă)`

**Body**:
```
Bună Ruslan,

După meetingul lung din februarie pe MyLife+ și după ce am promis că revin cu o variantă care rezolvă în mod fundamental partea de confidențialitate, iată ce am construit între timp.

Pe 18 mai publicăm MD-Chat — un workspace intern E2EE construit pe Matrix, cu layer AI confidențial. Pentru MyLife+, asta înseamnă în concret:

- Camera pacienți×case manager criptată end-to-end. Mega nu poate citi. Inițiativa Pozitivă nu poate citi (până când case manager-ul nu deschide app-ul). Nimeni altcineva nu poate citi.
- AI „self-mode" opțional pentru pacient — un Digital Twin care răspunde la întrebări frecvente (program tratament, întrebări sociale, suport psihologic) cu fallback la operator uman când subiectul depășește scope-ul.
- Cărți de sănătate digitale — mini-app sigură pentru retete, programări CDSI, fără ca datele să iasă pe Telegram (unde sunt acum).
- Conformitate Legea RM 195/2024 art. 9 pentru date sensibile sănătate, automat. Nu mai e o decizie pe fiecare angajat — e infrastructura.

Pentru Inițiativa Pozitivă, asta poate fi proiectul pilot care vă justifică un grant separat (UNAIDS, UE EaP, USAID dacă revine). Pot facilita contactul cu programul NLnet și cu departamentul digital health al UE.

20 min săptămâna 19–23 mai pe Zoom? Trei sloturi: marți 20 mai 16:00, miercuri 21 mai 13:00, joi 22 mai 10:00.

Mulțumesc, te apreciez,
Oleg
+373 60 00 00 00
```

Show → GO → Send.

## Report when done

```
[TASK B9] ✅ B2B wave 1 — 5 emails sent.

What I did:
  - Composed 5 personalized emails from oleg@megapromoting.com
  - Each shown to Oleg before sending; explicit "GO" received per email
  - Sent at <timestamps>
  - Subject lines consistent format

Artifacts / links produced:
  - MSA Credit (Gheorghe Bunescu) — sent <timestamp>
  - Aquadis (Vlad Manea) — sent <timestamp>
  - CrediteMD — sent <timestamp>
  - PharmaHerb (Andrei [Nume]) — sent <timestamp>
  - MyLife+ (Ruslan Poverga) — sent <timestamp>

Next manual step for Oleg:
  - Wait 3 business days for replies
  - Schedule any 20-min calls that get requested
  - Wave 2 (Esushi, Anticolect, IcebergDent, BigSportGym, CipAuto) scheduled for D9 of Sprint 0 (~26 May)
  - Cronberry tag for tracking: md-chat-warm-outreach-wave-1
```

# ============================================================
# TASK B6 — 4 letters of intent (PRIORITY P2)
# ============================================================

**Outcome**: 4 formal letters/emails sent: AGE Moldova (WE BUILD), Moldova IT Park, UTM Facultatea Calculatoare, MSA Credit (signed LoI). All from `oleg@megapromoting.com` via Gmail.

For each: compose, paste body, show Oleg, get GO, send.

## Letter 1 — AGE Moldova (WE BUILD slot request)

**To**: `office@egov.md`
**Cc**: `office@stisc.gov.md`
**Subject**: `Cerere participare program WE BUILD — produs MD-Chat (mesager sovereign Moldova)`

**Body**:
```
Către: Agenția de Guvernare Electronică (AGE)
Adresa: bd. Ștefan cel Mare și Sfânt 134, Chișinău, Republica Moldova
În atenția: Dl. Director General AGE / Dna. Director Adjunct relația cu sectorul privat
Cu copie: Serviciul Tehnologia Informației și Securitate Cibernetică (STISC)
De la: Mega Promoting SRL, prin Oleg Chetrean, CEO
Data: 22 mai 2026
Numărul de referință intern: MP-AGE-2026-001

Stimată conducere AGE,

Subsemnatul Oleg Chetrean, administrator și acționar al Mega Promoting SRL (IDNO disponibil la cerere, rezident al Parcului IT Moldova), vă adresez prezenta cerere oficială pentru includerea produsului nostru nou — MD-Chat — în programul WE BUILD anunțat de AGE, în calitate de relying-party al sistemului MPass.

1. Despre Mega Promoting SRL

Mega Promoting SRL este o companie moldovenească activă din 2017, rezident al Parcului IT Moldova din 2019, specializată în produse software cu componentă de inteligență artificială. În producție rulăm patru produse:

- aichat.md — platformă de chatboți AI integrată în WhatsApp, Facebook, Telegram, Instagram, SMS, cu peste 100.000 mesaje procesate zilnic și zeci de clienți business moldovenești (sector retail, IFN, servicii medicale, educație, sport, automotive).
- Cronberry — platformă de analiză conversațională cu LLM.
- Kallina — asistent vocal AI utilizat de instituții financiare, spitale și call-center.
- Router by MP — gateway LLM multi-provider cu politică de markup transparentă.

Echipa: 8 persoane în Chișinău. Auditul GDPR intern din februarie 2026 a identificat 23 de lacune, dintre care 18 sunt deja remediate, iar restul se închid în iunie 2026, în coordonare cu reprezentantul nostru UE conform art. 27 GDPR (Prighter SARL, Bruxelles).

2. Despre MD-Chat

MD-Chat este o platformă de mesagerie sovereign EU-grade, construită în Moldova pe stivă tehnologică deschisă (Matrix Synapse + Element X + libsignal + MLS RFC 9420 + PQXDH post-quantum), cu un layer de inteligență artificială integrat confidential compute derivat din Cronberry. Lansarea publică a codului sursă: 18 mai 2026. Beta privată cu primii utilizatori: T4 2026. Release stabil 1.0: T2 2027.

Obiectivele declarate ale proiectului:

1. Oferirea unei alternative sovereign față de Telegram (platformă regulatoriu fragilă după arestarea Pavel Durov din 24 august 2024), Viber (proprietate Rakuten Japonia) și WhatsApp (Meta, sub jurisdicție SUA).
2. Integrare nativă cu ecosistemul digital moldovenesc: EVO, MPass, MSign — primul mesager comercial care implementează acest stack.
3. Pre-conformitate cu obligațiile UE care intră în vigoare în următoarele 12 luni: Regulamentul (UE) 2024/1689 (AI Act) art. 50 — 2 august 2026; Regulamentul (UE) 2023/1543 (eEvidence) — 18 august 2026; Regulamentul (UE) 2024/2847 (Cyber Resilience Act) — 11 septembrie 2026; alinierea Legii RM nr. 195/2024 — 23 august 2026.
4. Suport bilingual nativ — română și rusă.
5. Open source integral: server și client sub AGPLv3, layer AI sub Apache 2.0.

Codul este public din 18 mai 2026 la github.com/olegchetrean/md-chat. Site-ul de produs: md-chat.eu.

3. Cererea concretă

Solicităm includerea MD-Chat ca relying-party MPass în programul WE BUILD, cu următoarele specificații tehnice:

- Service Provider Entity ID: https://msg.md-chat.eu/saml/sp
- Niveluri de autentificare suportate: LOA2 (substantial) la signup; LOA3 (high) pentru funcții premium
- Atribute solicitate (data minimization): verified (boolean) · age_band (interval, nu data exactă) · prenume
- Atribute pe care NU le solicităm: IDNP, adresa, numele complet, data nașterii exactă
- Use case: badge „Verified by EVO" pentru utilizatori MD, opțional la signup
- Timeline cutover beta: T4 2026 (octombrie–decembrie)
- Timeline producție: T2 2027

4. Beneficii pentru cetățean, stat și ecosistem

Pentru cetățean: identitate verificată EVO asociată unui messenger sovereign, fără să-și expună IDNP-ul către operatorul privat.
Pentru stat: extindere ecosistem digital prin partener IT Park, cost zero pentru stat.
Pentru AGE și STISC: validare WE BUILD prin caz de utilizare emblematic; pilot pentru integrarea eIDAS 2.0 Digital Identity Wallet (obligativitate UE din 2027).

5. Pași următori solicitați

1. O întrevedere de 30 de minute în luna iunie 2026, de preferință în săptămâna 8–12 iunie (după Moldova Digital Summit).
2. Comunicarea documentației tehnice solicitate de AGE pentru relying-party MPass.
3. Comunicarea timeline-ului estimat de aprobare.
4. Eventual, un punct de contact tehnic dedicat la AGE/STISC.

6. Deadline practic

Pentru a putea integra răspunsul AGE în aplicația noastră la NLnet NGI Zero Commons Fund cu deadline 30 mai 2026, am aprecia un acuz de primire în 5 zile lucrătoare și o invitație la întrevedere până la 7 iunie 2026.

Vă mulțumesc pentru atenția acordată.

Cu respect,

Oleg Chetrean
CEO, Mega Promoting SRL
Membru Parcul IT Moldova
oleg@megapromoting.com · +373 60 00 00 00
Chișinău, Republica Moldova
```

Show → GO → Send.

## Letter 2 — Moldova IT Park (Vitalie Tarlev)

**To**: ask Oleg for the email (try `info@itpark.md` or direct to Vitalie Tarlev)
**Subject**: `Solicitare scrisoare de susținere proiect MD-Chat pentru aplicație NLnet (UE)`

**Body**:
```
Către: Domnului Vitalie Tarlev, Director General Moldova IT Park
Cu copie: secretariat@moldovaitpark.md
De la: Mega Promoting SRL, prin Oleg Chetrean, CEO
Data: 20 mai 2026
Urgență: cerere de răspuns până la 25 mai 2026 inclusiv

Stimate Domnule Director Tarlev,

Subsemnatul Oleg Chetrean, administrator al Mega Promoting SRL (rezident Moldova IT Park), vă adresez cu respect prezenta solicitare pentru o scrisoare de susținere instituțională din partea Moldova IT Park pentru proiectul nostru MD-Chat.

1. Contextul cererii

Lansăm pe 18 mai 2026 un produs nou — MD-Chat — o platformă de mesagerie sovereign EU-grade open source, construită în Moldova pe protocolul Matrix, cu integrare nativă a sistemului de identitate EVO/MPass și un layer de inteligență artificială confidențial derivat din produsul nostru existent Cronberry.

Aplicăm pentru o finanțare europeană de 30.000 EUR la NLnet NGI Zero Commons Fund — un fond gestionat de NLnet Foundation (Olanda) cu sprijinul Comisiei Europene. Deadline-ul aplicației: 30 mai 2026.

Una dintre cerințele aplicației este atestarea unui ecosistem instituțional care susține proiectul. Scrisoarea Moldova IT Park va fi parte integrantă a dosarului de aplicație.

2. Ce solicităm concret

O scrisoare de susținere de maximum 1 pagină, în limba română sau engleză (preferabil engleză pentru NLnet), care să confirme:

1. Mega Promoting SRL este rezident activ Moldova IT Park în domeniul Software Development & AI.
2. Sectorul IT&AI moldovenesc are nevoie strategică de produse software sovereign open source.
3. Moldova IT Park încurajează și susține astfel de inițiative ale rezidenților care vizează piața UE.
4. Lansarea publică a MD-Chat reprezintă un caz de utilizare emblematic al ecosistemului IT Park.

Nu vă cerem cofinanțare, garanție sau angajament financiar. Scrisoarea este un act de validare instituțională.

3. Beneficii reciproce

Pentru Moldova IT Park: vizibilitate internațională în ecosistemul FOSS european; showcase pentru investitori și potențialii rezidenți noi; atragere de talent; poziționare ca hub sovereign tech CEE.

4. Despre Mega Promoting și MD-Chat

Suntem 8 persoane în Chișinău, rezidenți IT Park, cu patru produse în producție: aichat.md, Cronberry, Kallina, Router by MP. MD-Chat este construit pe protocolul Matrix (folosit de Tchap Franța, BwMessenger Germania, gematik TI-Messenger Germania, BEAM Belgia — toate produse sovereign EU). Repository public din 18 mai 2026: github.com/olegchetrean/md-chat. Site: md-chat.eu. Pilot prezentat la Moldova Digital Summit 5–6 iunie 2026.

5. Termen de răspuns

Pentru a putea atașa scrisoarea la aplicația NLnet (deadline strict 30 mai 2026), am aprecia primirea documentului semnat până la data de 25 mai 2026 inclusiv.

Sunt complet disponibil pentru o discuție telefonică, întâlnire scurtă în săptămâna 19–23 mai, sau pentru a furniza un draft al scrisorii care echipa juridică IT Park să-l rafineze.

Vă mulțumesc pentru atenția acordată.

Cu deosebită considerație,

Oleg Chetrean
CEO, Mega Promoting SRL
Membru Moldova IT Park
oleg@megapromoting.com · +373 60 00 00 00
```

Show → GO → Send.

## Letter 3 — UTM Facultatea Calculatoare

**To**: ask Oleg for the dean's email (try `decanat.fcim@utm.md` or `info@utm.md`)
**Subject**: `Parteneriat academic + scrisoare susținere proiect MD-Chat`

**Body**:
```
Către: Domnului Decan al Facultății Calculatoare, Informatică și Microelectronică (FCIM) — UTM
Cu copie: Prorectorul cercetare UTM · rectorat@utm.md
De la: Mega Promoting SRL, prin Oleg Chetrean, CEO
Data: 20 mai 2026
Urgență: cerere de răspuns până la 25 mai 2026 (pentru anexare la aplicația NLnet)

Stimate Domnule Decan,

Subsemnatul Oleg Chetrean, fondator și CEO al Mega Promoting SRL (rezident Parcul IT Moldova), vă adresez prezenta cerere de parteneriat academic pentru proiectul nostru nou MD-Chat — un mesager sovereign open source EU-grade, construit în Moldova pe protocolul Matrix cu integrare nativă a sistemului de identitate EVO/MPass.

1. Despre proiect

MD-Chat este o platformă de comunicare sigură (mesagerie text, voce, video) cu următoarele componente tehnice:

- Server: Synapse fork sub AGPLv3 (Python).
- Clienți: Element X fork sub AGPLv3 (Rust, Swift, Kotlin).
- Criptare end-to-end: libsignal, MLS RFC 9420, PQXDH post-quantum (NIST FIPS 203).
- Layer AI confidențial: derivat din Cronberry, relicențiat Apache 2.0, rulând în confidential compute (modelul Apple PCC) cu attestation publică AMD SEV-SNP / Intel TDX.
- Identitate: integrare nativă EVO/MPass; suport eIDAS 2.0 din T1 2027.

Lansare publică a codului: 18 mai 2026. Repository: github.com/olegchetrean/md-chat. Aplicăm pentru o finanțare europeană de 30.000 EUR la NLnet NGI Zero Commons Fund, deadline strict 30 mai 2026.

2. Ce solicităm UTM-ului

Cerem un parteneriat academic structurat pe patru componente, pe care le putem activa pe rând sau simultan:

2.1 Scrisoare de susținere pentru NLnet (URGENT, deadline 25 mai 2026)

O scrisoare de maximum 1 pagină care confirmă:
- Mega Promoting este o companie tehnologică moldovenească credibilă.
- Proiectul MD-Chat reprezintă un caz de utilizare cu valoare academică, didactică și de cercetare relevantă pentru FCIM.
- UTM susține astfel de inițiative de produs sovereign open source.

2.2 Practică de licență și master pentru 2–4 studenți (T3–T4 2026)

Teme candidate:
- Implementare PQXDH în clientul Android.
- Layer federated identity — bridge între EVO/MPass (SAML 2.0) și OIDC.
- Confidential compute attestation pentru AI layer.
- Static analysis pe Synapse fork — integrare CodeQL + Semgrep + fuzz harness.

2.3 Curs invitat în semestrul de toamnă 2026

Prelegere de 90 de minute pe tema „Arhitectura unui mesager sovereign EU-grade: criptografie, identitate federată, AI confidențial, conformitate UE".

2.4 Conexiune Erasmus+ cu TU Darmstadt (CYSEC), ETH Zürich, EPFL, TU Wien.

3. Beneficii pentru FCIM

Vizibilitate internațională în rețeaua FOSS UE, plasament studenți la angajator local, co-publicare academică (FOSDEM, EuroPython, USENIX, IEEE EuroS&P), validare didactică.

4. Termen de răspuns

Pentru anexarea scrisorii la aplicația NLnet, am aprecia primirea scrisorii până la 25 mai 2026 inclusiv. Sunt complet disponibil pentru discuție telefonică, întâlnire la sediul FCIM, sau pentru a furniza un draft de scrisoare.

Vă mulțumesc pentru atenția acordată.

Cu deosebită considerație,

Oleg Chetrean
CEO, Mega Promoting SRL
oleg@megapromoting.com · +373 60 00 00 00
```

Show → GO → Send.

## Letter 4 — MSA Credit Letter of Intent (B2B pilot)

**To**: `gheorghe.bunescu@msacredit.md`
**Cc**: `gheorghe.2@msacredit.md`
**Subject**: `Letter of Intent — Kallina Sovereign Workspace pilot pentru MSA Credit`

**Body**:
```
Bună Gheorghe,

În continuarea discuției pe care urmează să o avem despre extinderea contractului MSA prin MD-Chat, atașez o Letter of Intent (LoI) — un document care:

- Confirmă intenția neobligatorie a MSA Credit de a fi primul pilot B2B pentru MD-Chat.
- NU creează obligație financiară.
- Permite Mega să anexeze documentul la aplicația NLnet NGI Zero Commons Fund (deadline 30 mai 2026, finanțare 30.000 EUR pentru proiect open source).

Mai jos varianta completă a textului. Dacă ești OK cu conținutul, putem semna prin MSign (1 minut, ambele părți) sau imprima și semna fizic.

---

LETTER OF INTENT — Pilot B2B MD-Chat pentru MSA Credit

Parte 1: Mega Promoting SRL, IDNO disponibil la cerere, cu sediul în Parcul IT Moldova, Chișinău, reprezentată legal de Oleg Chetrean, administrator („Furnizorul" sau „Mega").

Parte 2: MSA Credit SRL, cu sediul în Chișinău, reprezentată legal de Gheorghe Bunescu, CEO („Beneficiarul" sau „MSA").

Subiect: Intenție de pilot pentru utilizarea platformei MD-Chat ca workspace intern E2EE cu AI confidențial integrat, în extensie a contractului Etapa 1 semnat la 14 mai 2026.

Caracter: scrisoare de intenție neobligatorie din punct de vedere financiar — document de poziționare strategică, anexabil la aplicația NLnet.

1. Context

Mega și MSA au semnat la 14 mai 2026 un contract pentru Etapa 1 a proiectului OpenClaw + Copilot operator, cu cinci componente acceptate. În paralel, Mega lansează pe 18 mai 2026 un produs nou, open source: MD-Chat — platformă de mesagerie sovereign EU-grade construită pe Matrix, cu layer AI confidențial derivat din Cronberry.

MD-Chat este compatibil arhitectural cu obiectivele Etapa 1 MSA: jurisdicție clară Moldova/UE, criptare end-to-end între utilizatori, AI care nu citește conținutul, conformitate GDPR + Legea RM 195/2024 + AI Act art. 50.

2. Intenția părților

Părțile își exprimă intenția neobligatorie de a explora utilizarea MD-Chat ca:

a) Shell intern E2EE pentru echipa MSA (analiști credit, risk officer, compliance, customer service, IT), pe care vor coexista componentele acceptate în Etapa 1.

b) Runtime pentru voice agents Etapa 2 (Maria + Alex×7 + Sofia), când MSA va decide trecerea de la AMÂNAT la activare.

c) Workspace pentru comunicare client-MSA opțional în cazuri sensibile financiar / KYC.

3. Calendar propus

- Etapa 0 — Discovery: săptămâna 26–30 mai 2026
- Etapa 1 — Setup tehnic: iulie–august 2026
- Etapa 2 — Pilot extins: septembrie–noiembrie 2026
- Decizie producție: decembrie 2026

4. Aspecte financiare

Nu creează obligație financiară.

Mega oferă MSA:
- Acces gratuit la MD-Chat în Etapa 1 (iulie–august 2026)
- Reducere de 50% la prețul de producție pentru primele 12 luni post-pilot
- Priority support direct cu echipa Mega în primii 18 luni
- Customization specific MSA

5. Confidențialitate și conformitate

- Toate datele MSA în MD-Chat sunt E2EE.
- Layer-ul AI rulează în confidential compute (Apple PCC pattern).
- Conformitate GDPR + Legea RM 195/2024.
- Reprezentant UE: Prighter SARL, Bruxelles.

6. Utilizare

- Poate fi anexat de Mega la aplicația NLnet și la viitoare aplicații UE.
- Menționare publică doar cu acord scris MSA pentru declarații specifice.

7. Caracter neobligatoriu

Niciuna dintre părți nu este obligată să continue. Notificare scrisă de 14 zile, fără penalitate.

8. Următoarea acțiune

În urma semnării, Mega va programa cu MSA întâlnirea Etapa 0 (Discovery, 30 minute, săptămâna 26–30 mai 2026).

---

Semnături

Pentru Mega Promoting SRL: ____________________ Oleg Chetrean, CEO, Data: ___________________
Pentru MSA Credit SRL: ____________________ Gheorghe Bunescu, CEO, Data: ___________________

---

Mulțumesc, Gheorghe.

Oleg
+373 60 00 00 00
```

Show → GO → Send.

## Report when done

```
[TASK B6] ✅ 4 letters sent.

What I did:
  - Composed 4 letters from oleg@megapromoting.com (AGE WE BUILD, IT Park, UTM, MSA Credit LoI)
  - Each shown to Oleg before sending
  - All sent with explicit "GO" confirmation

Artifacts:
  - AGE: <Gmail message ID>
  - IT Park: <ID>
  - UTM: <ID>
  - MSA: <ID>

Next manual step for Oleg:
  - Follow-up D+5 (24 May) if no reply from AGE / IT Park / UTM
  - Sign MSA LoI via MSign when Bunescu approves the text
```

# ============================================================
# TASK B10 — Pitch deck Google Slides + practice schedule (PRIORITY P3)
# ============================================================

**Outcome**: 12-slide Google Slides created at `docs.google.com/presentation` with the content below. 3 practice runs scheduled in Oleg's Google Calendar.

## Step 1 — Create the presentation

Open https://docs.google.com/presentation. Create new blank presentation. Title: `MD-Chat — Moldova Digital Summit 2026`. Apply theme manually: dark navy background `#1A2D4E`, teal accents `#2DD4BF`, white text. Font: Inter (or system sans-serif if Inter not available).

## Step 2 — Populate 12 slides

For each slide below: create the slide, title from the header line, body as bullet points. Add the speaker notes as Speaker Notes (View → Show Speaker Notes).

### Slide 1 — Hook
**Title**: `Moldova nu are mesager propriu.`
**Body**:
```
Franța are Tchap. Germania are BwMessenger. Belgia are BEAM. Italia are IO.
Ucraina are Diia.

Moldova folosește Telegram (Pavel Durov arestat Franța), Viber (Rakuten Japonia) și WhatsApp (Meta).

În 2026, asta e un risc de securitate de stat.
```
**Speaker notes**: pauză 3 secunde. Lasă să se așeze.

### Slide 2 — Problema
**Title**: `Trei crize concurente pentru comunicarea sovereign în Moldova`
**Body**:
```
🔴 Telegram fragil regulator — Pavel Durov arestat 24 aug 2024 în Paris. Telegram cooperează acum cu autoritățile UE pe IP + phone. Dominanța Telegram în comunicarea politică MD = risk geopolitic.

🟡 EU compliance wall iunie-august 2026 — AI Act Art 50 (2 aug), eEvidence Regulation (18 aug), CRA reporting (11 sept). Niciun messenger folosit actual în MD nu e compliant by design.

🟢 Oportunitate sovereign de aur — UE finanțează agresiv mesageria sovereign (NLnet, Sovereign Tech Fund DE, Horizon Europe). MD-Chat poate beneficia ca țară candidate UE.
```

### Slide 3 — Soluția
**Title**: `MD-Chat — mesager sovereign EU-grade, construit în Moldova`
**Body**:
```
🇲🇩 + 🇪🇺 + 🤖

E2EE messenger (Matrix + Signal protocol)
+ Confidential AI (Cronberry-derived layer)
+ EVO/MPass identity
+ eIDAS Wallet ready (2027)
+ Compliance from Day 1

Diferențiator unic global: niciun messenger EU n-are AI nativ confidențial.
Niciun messenger n-are Verified Authentic Digital Twin (avatar AI atestat eIDAS).
```

### Slide 4 — De ce acum
**Title**: `Trei deadline-uri 2026 care fac aceasta inevitabil`
**Body**:
```
2 aug 2026 — AI Act Art 50 enforceable — toți chatbots / voice agents must declare AI
18 aug 2026 — eEvidence Regulation — production order portal mandatory
23 aug 2026 — Moldova Law 195/2024 GDPR — aliniere completă cu UE
11 sept 2026 — CRA 24h vuln disclosure — software certification obligatorie
11 dec 2027 — CRA full conformity — CE marking software UE
2027 — EUDI Wallet mandatory — identity layer continental

MD-Chat designed pentru toate aceste deadline-uri din Day 1.
```

### Slide 5 — Cum
**Title**: `Stack-ul standardizat global`
**Body**:
```
8. Social (stories, channels, communities)
7. Commerce (CRM port, business AI twins)
6. Government (EVO, MPass, MSign, MDelivery)
5. AI Layer (Cronberry-derived, confidential compute)
4. Apps (mini-apps + MCP bots)
3. Payments (Wero + SEPA + MIA)
2. Identity (EVO + MPass + eIDAS Wallet)
1. Transport (E2EE Matrix + libsignal + MLS)

Toate componentele open source: AGPLv3 (server, client) + Apache 2.0 (AI layer)
```

### Slide 6 — Ce e diferit la MD-Chat
**Title**: `3 lucruri pe care NIMENI altul nu le are`
**Body**:
```
🤖 Digital Twin atestat eIDAS — fiecare user își poate face un AI clone care răspunde 24/7 cu atestare de identitate calificată. Nimic similar în Apple Intelligence / Meta AI / Google Gemini.

🔐 Confidential AI pe group chats — sumarizare grup + sentiment + action items rulează într-un enclave verificabil fără ca operatorul mesageriei să vadă conținutul.

🇲🇩 EVO + MPass native — singurul messenger cu integrare cu identitatea digitală a Moldovei din Day 1.
```

### Slide 7 — Cine sunt în spate
**Title**: `Mega Promoting SRL — IT Park Moldova`
**Body**:
```
4 produse production, toate AI-driven:
- aichat.md — 84+ clienți B2B
- Cronberry — knowledge graph 17.8k contacte, digital twins
- Kallina — voice AI agents pentru bănci MD
- Router by MP — AI gateway 16+ providers

Echipa: 8 inj, bilingual RO/RU, Moldova IT Park (7% tax)

Track record financiar: cash-flow pozitiv 5+ ani, 100+ clienți activi
```

### Slide 8 — Cerere către Stat
**Title**: `3 cereri concrete către STISC / AGE / Ministere`
**Body**:
```
1. WE BUILD relying-party slot (gratis pentru MD-Chat)
   - 1 din 8 slot-uri WE BUILD încă deschise
   - Beneficiu: integrare EVO + MPass native, "Verified by EVO" badge
   - Cost stat: €0

2. Pilot "MD-Chat for Civil Servants" — Tchap model
   - Mandat pentru funcționari de la 1 ministru
   - 200-2.000 users pilot, scalabil 25-30k post-pilot
   - Cost stat: €0 (free tier pentru gov)

3. Procurement contract "MD-Chat Sovereign Workspace"
   - Pentru ministere + STISC, valoare €600k-1.2M
   - On-premise + SecNumCloud-equivalent + 24/7 support
   - Replicarea modelului francez Tchap operatorial
```

### Slide 9 — Plan execuție
**Title**: `12 luni roadmap`
**Body**:
```
Q3 2026 (M0-M3)
- NLnet €30k grant submitted (30 mai)
- Public repo + brand (18 mai)
- AI compliance launch (2 aug)
- MVP B2B 5 paying customers

Q4 2026 (M4-M6)
- EVO/MPass beta live
- 10 B2B paying
- Prototype Fund DE €47k

Q1 2027 (M7-M9)
- EUDI Wallet integration
- Public beta 1k-10k users
- Sovereign Tech Fund €200k+

Q2 2027 (M10-M12)
- Stable 1.0 launch
- Romanian expansion
- Horizon Europe consortium €1-5M

Bootstrap cost cash: €0 cumulat first 12 months
```

### Slide 10 — Beneficii
**Title**: `Win-win-win`
**Body**:
```
Pentru cetățean:
- Mesaj sovereign + privat by default
- AI features integrate transparent
- Verified identity Moldova + UE
- Servicii stat la 1 click în chat

Pentru stat:
- Comunicare guvernamentală securizată (Tchap model)
- Conformitate UE pre-built
- Reducere dependență platforme rusești / japoneze / americane
- Soft-power digital regional

Pentru sectorul IT:
- Showcase Moldova IT Park
- Open source export
- Atragere talent + finanțare UE
```

### Slide 11 — Call to action
**Title**: `Următorul pas`
**Body**:
```
Discuție 30 min cu STISC executive — în luna iunie 2026

Agendă propusă:
1. WE BUILD slot application formal
2. Pilot Civil Servants un ministru
3. Procurement framework pentru contract sovereign workspace

Email contact: oleg@megapromoting.com
Repo public: github.com/olegchetrean/md-chat
```

### Slide 12 — Mulțumiri
**Title**: `"Moldova merită un messenger pe care îl putem deține."`
**Body** (centrat):
```
MD-Chat
github.com/olegchetrean/md-chat
md-chat.eu (în curs)
contact@md-chat.eu

Mulțumiri.
Întrebări?
```

## Step 3 — Schedule 3 practice runs

Open https://calendar.google.com. Create 3 events:

1. **Practice 1 — Pitch alone (timing)** — 28 mai 2026, 14:00–15:00 EEST, 1h block
   Description: "Solo practice. Time the talk to 12 minutes. Identify weak transitions."

2. **Practice 2 — Pitch with team feedback** — 1 iunie 2026, 14:00–15:30 EEST, 1.5h block
   Description: "Practice with 2 colleagues for feedback. Iterate after Q&A simulation."

3. **Practice 3 — Final dry run** — 4 iunie 2026, 14:00–15:30 EEST, 1.5h block
   Description: "Final dry run with mocked Q&A. Ready to deliver next day."

For each event: confirm with Oleg before saving.

## Report when done

```
[TASK B10] ✅ Pitch deck created + practice runs scheduled.

What I did:
  - Created Google Slides "MD-Chat — Moldova Digital Summit 2026"
  - Populated 12 slides per inline content
  - Applied dark navy + teal theme
  - Created 3 practice run calendar events (28 mai, 1 iunie, 4 iunie)

Artifacts:
  - Slides URL: <copy from browser>
  - Calendar events created

Next manual step for Oleg:
  - Add visual mockups on slides 3, 5, 6, 9, 11 (need a designer or use built-in shapes)
  - Print 50-100 one-pager PDFs for distribution at Summit
  - Final delivery: 5-6 iunie 2026 Moldova Digital Summit
```

# ============================================================
# FINAL REPORT — write this at the very end
# ============================================================

After all tasks (or as many as you got through), write a final summary in this exact format:

```
================================================================================
SPRINT 0 EXTERNAL TASKS — FINAL REPORT
================================================================================
Date: <today>
Operator: Oleg Chetrean
Session duration: <total-minutes>

TASK STATUS:
  B4 Infobip          [ ✅ / ⏸️ / ❌ / ⏭️ ]   <one-line outcome>
  B8 NLnet            [ ✅ / ⏸️ / ❌ / ⏭️ ]   <one-line outcome>
  B3 Mastodon         [ ✅ / ⏸️ / ❌ / ⏭️ ]   <one-line outcome>
  B9 B2B emails       [ ✅ / ⏸️ / ❌ / ⏭️ ]   <X/5 sent>
  B6 Letters          [ ✅ / ⏸️ / ❌ / ⏭️ ]   <X/4 sent>
  B10 Pitch deck      [ ✅ / ⏸️ / ❌ / ⏭️ ]   <one-line outcome>

CRITICAL FOLLOW-UPS (within 7 days):
  - <list any actions Oleg must do himself>

ARTIFACTS PRODUCED (links/IDs):
  - Mastodon: <URL>
  - NLnet reference: <ID>
  - Infobip application: <ID>
  - Gmail message IDs (letters + B2B): <list>
  - Google Slides: <URL>

NEXT SESSION (Sprint 0 wave 2, around 25-27 May):
  - B9 wave 2 (5 more B2B clients: Esushi, Anticolect, IcebergDent, BigSportGym, CipAuto)
  - Follow-ups on AGE / IT Park / UTM (if no reply yet)
  - Final NLnet review before 28 May deadline if you couldn't submit today
================================================================================
```

# Final notes

- If you don't have browser access, tell Oleg "I don't have browser access in this environment — I'll generate per-step instructions for you to execute manually" and convert each task into a numbered checklist for him.
- If you have terminal access (Codex CLI), you can still complete tasks B4, B8, B3, B6, B10 via curl-style or HTTPS calls where APIs exist (limited). B9 still requires Gmail.
- If you're Codex Cloud running in a remote VM with no browser, tell Oleg honestly — most of these tasks need a real browser.
- Always favour explicit confirmation over assumption. If unsure, ask.
- Make the user feel calm and in control. This is a critical deadline week.

=== END CODEX PROMPT ===
```

---

## Cum folosești promptul mai sus

### Mod A — Codex Cloud (ChatGPT browser-based agent)

1. Mergi la https://chatgpt.com și activează Codex (sau https://codex.openai.com dacă există ca portal separat — verifică în ChatGPT).
2. Start a new Codex session with browser mode enabled.
3. Copiază TOT conținutul de la `=== BEGIN CODEX PROMPT ===` până la `=== END CODEX PROMPT ===` (cele ~25k cuvinte de mai sus).
4. Paste într-un singur mesaj.
5. Codex va citi tot și va începe cu B4 (Infobip).
6. Răspunde interactiv când îți cere credentials / 2FA / confirmare per acțiune.

### Mod B — Codex CLI local (dacă Codex Cloud nu are browser)

1. Install: `npm install -g @openai/codex` (sau echivalent — verifică docs la momentul lansării)
2. `codex --browser` (sau flag echivalent pentru a activa browser tool)
3. Paste promptul mai sus
4. Aceeași execuție interactivă

### Mod C — Manus / Devin / Cursor / orice browser-agent generic

Funcționează la fel. Paste promptul. Toate informațiile inline.

### Mod D — Dacă agentul NU are browser

Promptul are o instrucțiune la final: "If you don't have browser access, tell Oleg «I'll generate per-step instructions for you to execute manually»". Agentul va converti cele 6 task-uri într-un checklist numerotat pe care îl poți face manual.

## Cost estimat

| Component | Tokens | Cost approximate |
|-----------|--------|------------------|
| Input prompt (acest fișier) | ~25.000 | $0.075 (Sonnet 4.5) / $0.25 (Opus) |
| Output dialog cu Oleg | ~10.000 | $0.15 / $0.50 |
| Multiple turns interactive (~50-100 schimburi) | ~50.000 cumulat | $0.75 / $2.50 |
| **TOTAL pe sesiune** | | **~$1-5** (Sonnet) / **~$10-25** (Opus) |

## Pre-flight checklist înainte să rulezi Codex

- [ ] Mac la birou, Gmail logged in ca `oleg@megapromoting.com`
- [ ] 1Password / Bitwarden unlocked (pentru Infobip credentials)
- [ ] Telefon la îndemână pentru 2FA codes
- [ ] 3-4 ore alocate fără interrupții
- [ ] Brand assets (logo, og-image) accesibile pe Mac sub `/Users/macbook_nou/Projects/md-chat/brand/`

## Live link

📄 Acest prompt este versionat în repo public:
**https://github.com/olegchetrean/md-chat/blob/main/docs/browser-agent/CODEX-PROMPT.md**

Poți accesa-l de pe orice device, copia într-un mesaj Codex, fără să fie nevoie să muți fișiere între device-uri.

---

*Generat 18 mai 2026 ca parte din Sprint 0 deliverables MD-Chat.*
*Licensed CC-BY-SA 4.0. Reuse welcome.*
