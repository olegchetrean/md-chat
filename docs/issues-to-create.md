# Issues to create on GitHub (Sprint 0 + community)

> Drafts ready to paste into https://github.com/olegchetrean/md-chat/issues/new
> Run `gh issue create` per item once you're ready to make them public.

## Labels to create first

```bash
gh label create "sprint-0"        --color "FBBF24" --description "Sprint 0 (May 18-30, 2026)"
gh label create "good first issue" --color "7057ff" --description "Good for newcomers" --force
gh label create "help wanted"     --color "008672" --description "Extra attention is needed" --force
gh label create "compliance"      --color "d73a4a" --description "GDPR / AI Act / eEvidence / CRA"
gh label create "ai-layer"        --color "2DD4BF" --description "AI layer (Cronberry-derived)"
gh label create "identity"        --color "1E40AF" --description "EVO / MPass / eIDAS"
```

---

## Issue 1 — Sprint 0: rebrand Synapse strings (good first issue)

**Labels**: `good first issue`, `help wanted`, `sprint-0`

**Body**:
```
Synapse is forked vanilla. We need to rebrand user-visible strings to MD-Chat: client static pages, email templates, default room/account names.

Skills: Python (read-only) + HTML/CSS.

This is a great first issue — single-file scope, no internals knowledge required. See https://github.com/element-hq/synapse for upstream structure.
```

---

## Issue 2 — Sprint 1: port Cronberry Digital Twin engine

**Labels**: `ai-layer`, `help wanted`

**Body**:
```
Port the Digital Twin engine from the Cronberry codebase (Mega Promoting internal) into ai-layer/src/md_chat_ai/agents/.

Key changes:
- Refactor profile_generator.py for self-twin data (user's own messages, not contacts')
- Adapt memory.py for E2EE compatibility (encrypted memory store)
- New mode: business_24_7 (corporate AI agent)
- New mode: vacation (auto-reply with custom message)
- Disclosure: explicit AI Act Art 50 compliance at every twin reply

Skills: Python, basic LLM ops, Pydantic.

Owner pending. Cronberry source at internal Mega repo.
```

---

## Issue 3 — Sprint 2: phone verification via Infobip + TOTP MFA

**Labels**: `identity`, `sprint-0`, `help wanted`

**Body**:
```
Implement signup flow Step 2 (phone OTP) and Step 5 (TOTP MFA) per docs/architecture.md.

Pattern: port phone-verification.service.ts from Router by MP (Mega's existing AI gateway).

- Infobip multi-application: new sender ID 'MDChat'
- GSM-7 alphabet only (no diacritice in SMS body)
- Rate limits: 60s cooldown, 5/hr per phone, 5 verify attempts per code
- TOTP: RFC 6238 with 8 backup codes
- E.164 normalization with 24 country codes (MD/RO/UA/RU + EU)

Skills: TypeScript / Python, Infobip API.
```

---

## Issue 4 — Sprint 4: AI Act Art 50 disclosure UI + GPAI documentation

**Labels**: `compliance`, `sprint-0`

**Body**:
```
Hard deadline: 2 August 2026.

Required:
- Audio disclosure at start of every Kallina voice call ('Sunteti in legatura cu un agent AI MD-Chat')
- Text disclosure in chat on first message with AI feature
- Settings page 'AI Features' with list + toggle per feature
- GPAI obligations: model card transparency published
- Watermark AI-generated content (machine-readable)
- Update Privacy Notice with AI section explicit
- Update Terms with AI usage rights

Reference: Regulation (EU) 2024/1689 Article 50.
```

---

## Issue 5 — Sprint 4: eEvidence Regulation production order portal

**Labels**: `compliance`, `sprint-0`

**Body**:
```
Hard deadline: 18 August 2026.

Required:
- 24/7 portal at /legal/eu-evidence
- 8-hour emergency response SLA tracking
- Preservation order handling flow
- Internal runbook for receipt → triage → response
- Train Mega team on eEvidence procedures
- Test scenario with mock LEA request
- Audit log per request (Art 33 internal register)
- EU Representative contracted (Prighter Brussels)

Reference: Regulation (EU) 2023/1543.
```

---

## Issue 6 — Sprint 6: MPass SAML 2.0 → OIDC bridge for EVO Verify

**Labels**: `identity`, `help wanted`

**Body**:
```
Implement the WE BUILD relying-party integration with Moldova MPass.

Architecture:
- SAML 2.0 Service Provider (using egov-moldova/AGE.AspNetCore.MPass.Saml library)
- Internal SAML→OIDC bridge so Synapse can consume it
- Attributes released: { verified: true, age_band, prenume } — NO IDNP
- 'Verified by EVO' badge in user profile

Pending: WE BUILD slot approval from AGE (letter sent 21 May).

Skills: SAML, OIDC, Moldova government context.
```

---

## Quick batch-create script

```bash
# Run AFTER you've reviewed each issue text above:
gh issue create --title "Sprint 0: rebrand Synapse strings (good first issue)" \
  --label "good first issue,help wanted,sprint-0" \
  --body-file <(sed -n '/^## Issue 1/,/^## Issue 2/p' docs/issues-to-create.md | sed '1,/^Body.*:$/d' | sed '/^```$/d')

# (Repeat per issue, or use a loop.)
```

Alternative: copy/paste into the GitHub web UI at https://github.com/olegchetrean/md-chat/issues/new
