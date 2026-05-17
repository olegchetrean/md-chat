# MD-Chat — Voice & Tone Guide

> Companion to `brand/README.md`. Source of truth: `Reports/2026-05-17-EU-Messengers/Drafts/03-Brand-Spec-MDChat.md` §5.

## 1. Voice (constant across all copy)

MD-Chat sounds like a **competent, bilingual, technically transparent peer** — not a corporation, not an activist, not a startup bro.

Four pillars:

1. **Confident, not arrogant** — we know what we built; we don't insult competitors.
   - YES: "MD-Chat keeps your messages private."
   - NO:  "Other messengers spy on you."
2. **Concrete, not jargonist** — show, don't acronym-bomb.
   - YES: "Messages are end-to-end encrypted with the same protocol as Signal."
   - NO:  "We use X3DH-PQXDH-MLS-AES256-GCM."
3. **Bilingual native** — Romanian and Russian feel equally first-class; never machine-translated.
4. **Transparently technical when it matters** — we link to GitHub, RFCs, audit reports.

## 2. Tone (modulates with context)

| Context                     | Tone                              | Example |
|-----------------------------|-----------------------------------|---------|
| Onboarding                  | Warm, encouraging                 | "Bun venit. Let's set up your sovereign account in three steps." |
| Empty states                | Helpful, light                    | "No messages yet. Say buna to someone." |
| Error states                | Apologetic + actionable           | "We couldn't reach the server. Check your connection and tap retry." |
| Privacy explanations        | Calm, factual                     | "Your messages are encrypted on your device before they leave." |
| Marketing / landing         | Confident, slightly playful       | "Mesageria ta. Statul tău. Inteligența ta." |
| Legal / Terms               | Plain language, no jargon         | "We don't read your messages. We can't — they're encrypted." |
| AI Act Art 50 disclosure    | Neutral, informative              | "You are speaking with an AI assistant." |
| Outage / incident comms     | Direct, status-first, no PR spin  | "Calls are down. Cause: gateway timeout. ETA: 30 min." |

## 3. Forbidden phrases

| Phrase | Why |
|--------|-----|
| "revolutionary" | overclaim |
| "disrupt" | startup cliché |
| "bank-grade encryption" | meaningless, AML-tinted |
| "military-grade encryption" | meaningless cliché |
| "unhackable" | factually wrong, sets us up to fail |
| "web3" in consumer copy | wrong audience |
| "AI-powered", "AI-driven", "intelligent" | tell-don't-show; describe what the AI does |
| "world's first" | almost never true |
| "game-changer" | reviewer cliché, not product copy |

## 4. Preferred constructions

- "End-to-end încriptat" / "E2EE"
- "Designed in Moldova, EU-compliant"
- "Verified by EVO" badge — never invent equivalent badges
- "AI-ul tău, datele tale"
- "Sovereign messenger" — owns one strong adjective rather than four weak ones
- "Open source, audited" — paired, never alone

## 5. Bilingual rules

### Romanian (RO)
- Diacritice **always** correct: ă â î ș ț. Never "Inregistreaza-te".
- Modern verb forms; avoid 1990s officialese.
- Localize, don't translate: "Sign in" → "Conectează-te", not "Semnează în".

### Russian (RU)
- Cyrillic native. Never transliterate ("privet" is wrong; "привет" is right).
- **Ты** by default (informal messenger context).
- **Вы** for Business/Enterprise tier surfaces, legal text, and compliance prompts.

### English (EN)
- US English (color, organize, behavior).
- Sentence case for buttons: "Send message", not "Send Message".
- Oxford comma: yes.
- Avoid Britishisms in consumer copy ("whilst", "amongst").

### Internal copy (code, docs, commits)
- English, always. No exceptions.

## 6. Microcopy patterns

### Buttons (verbs first, sentence case)
- "Send message" / "Trimite mesaj" / "Отправить"
- "Verify identity" / "Verifică identitatea" / "Подтвердить"
- "Cancel" — never "Dismiss", never "Close" when "Cancel" fits.

### Confirmations
- Confirm destructive actions only. Don't ask before "Send".
- "Delete this conversation? This cannot be undone." — name the consequence.

### Empty states
- One sentence + one CTA. Never two.

### Notifications
- Subject + verb + object. "Maria sent you a photo." not "New message".

## 7. AI Act §50 disclosure (mandatory, non-negotiable)

When a user starts a conversation with a Kallina-powered bot:

- **RO**: "Vorbești cu un asistent AI. Răspunsurile pot fi imprecise."
- **RU**: "Вы общаетесь с ИИ-ассистентом. Ответы могут быть неточными."
- **EN**: "You are speaking with an AI assistant. Responses may be inaccurate."

Always paired with a 200ms warm disclosure tone before voice-agent speech.

## 8. Writing checklist (before publishing any user-facing copy)

- [ ] No forbidden phrases.
- [ ] Diacritics correct (RO) / Cyrillic native (RU).
- [ ] Sentence case on buttons.
- [ ] Tone matches the context table above.
- [ ] Linked to specifics (RFC, GitHub, audit) where claims are technical.
- [ ] If translated, a native speaker has reviewed — not just an LLM pass.
