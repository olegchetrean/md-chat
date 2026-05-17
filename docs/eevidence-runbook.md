# eEvidence Production-Order Portal — Operational Runbook

> **Regulation**: EU 2023/1543 (eEvidence Regulation), in force **18 August 2026**.
> **Companion regulation**: EU 2023/1544 (designation of EU Legal Representative).
> **Internal owner**: DPO (`dpo@megapromoting.com`).
> **External owner**: EU Representative — Prighter SARL, Brussels (`eu-rep@md-chat.eu`).
> **Backend module**: `md_chat_ai.eevidence`.
> **Public URL**: `https://md-chat.eu/legal/eu-evidence` → fronts the Flask blueprint.

---

## 1. Purpose

Every messenger that offers services to EU users must, from 18 August 2026:

1. Operate a **24/7 intake point** for European Production Orders (EPOC) and
   European Preservation Orders (EPOC-PR).
2. Designate at least one **establishment or legal representative** in the EU
   to receive and execute those orders (Art. 4 of EU 2023/1544).
3. Respond within the regulation's hard deadlines: **10 days standard, 8 hours
   in emergency** cases threatening life or critical infrastructure.
4. Keep an **internal register** of every order received and every action
   taken (Art. 31).
5. Publish a **bi-annual transparency report** with aggregated statistics
   (Art. 28 + Art. 32).

This runbook describes how MD-Chat operationalises those obligations through
the `md_chat_ai.eevidence` module and the surrounding human process.

## 2. Service-level deadlines (Art. 10)

| Urgency level | Deadline | Trigger | Audit event |
|---------------|---------|---------|-------------|
| **Standard**  | 10 days from receipt | Default for any EPOC | `order_received` |
| **Expedited** | Voluntary, ≤ 72 h | Authority requests faster turn-around without invoking emergency clause | `order_received` (urgency=expedited) |
| **Emergency** | **8 hours** from receipt | "Imminent threat to life or to critical infrastructure" (Art. 10(2)) | `order_received` (urgency=emergency) **or** `emergency_marked` if promoted later |

Standard tickets created by `ProductionOrderPortal.submit` carry a
`sla_deadline` equal to `received_at + 10 days`. Promoting a ticket via
`mark_emergency()` resets the deadline to `now + 8 hours` and writes an
`emergency_marked` entry in the audit chain. The watchdog cron (see §6) alerts
at T-30 minutes for emergency tickets and at T-24 h for standard tickets.

## 3. Refusal grounds (Art. 12)

The triage module (`md_chat_ai.eevidence.triage`) materialises every refusal
ground we may invoke as a `RefusalGround` enum value. The decision tree is
**advisory only** — formal refusal requires sign-off from DPO + CEO + EU Rep.

| Ground | Article | Triage trigger |
|--------|---------|----------------|
| `EXTRATERRITORIAL` | 12(1)(a) | Content order issued by state X targeting a user located in another country |
| `FUNDAMENTAL_RIGHTS` | 12(1)(b) | Charter violation — manual flag |
| `IMMUNITIES_PRIVILEGES` | 12(1)(c) | Target flagged `lawyer`, `mep`, `diplomat` |
| `NON_COMPLIANT_FORM` | 5, 9 + Annexes | Missing case_reference, short legal_basis |
| `THIRD_COUNTRY_CONFLICT` | 17 | Content disclosure target located in US / UK / CH |
| `PRESS_FREEDOM` | 12(1)(b) subset | Target flagged `journalist` / `press` |
| `DATA_CATEGORY_UNAUTHORIZED` | 5(4) | Administrative authority requesting traffic/content |
| `NON_EU_AUTHORITY` | 4 | Issuing state is not bound by the Regulation |

When the triage flags an order, the ticket lands in `under_review` (or
`emergency`) status and an alert is pushed to `#legal-eevidence` Matrix room
(MD-Chat homeserver) plus an email to DPO + EU Rep.

## 4. Escalation chain

```
authority submits order
        |
        v
[24/7 PORTAL]  ── auto-acknowledges, assigns EE-YYYYMMDD-XXXX ticket
        |
        v
[DPO]          ── triages within 1 h (4 h max on weekends);
                  if grounds for refusal → goes to EU Rep
        |
        +────────────────────┐
        |                    |
        v                    v
[EU REP — Prighter]   [Engineering on-call]
  Reviews legal       Extracts metadata / sub-IP logs / account info
  bases; drafts       under DPO supervision; encrypts artifacts.
  response or
  refusal.
        |
        v
[CEO]          ── final sign-off on outgoing response or formal refusal.
        |
        v
[ISSUING AUTHORITY] receives signed response via attachment_url + email
```

Roster contacts (live in 1Password vault `eevidence-roster`):

* DPO: Oleg Chetrean (acting) — `dpo@megapromoting.com`, +373 …
* Backup DPO: Lilia Chetrean — `lilia@megapromoting.com`
* EU Rep: Prighter SARL — `eu-rep@md-chat.eu`, +32 …
* CEO: Oleg Chetrean
* Engineering on-call: PagerDuty schedule `md-chat-legal`

## 5. Operator actions (operator-facing endpoints)

All endpoints below require the `X-MDChat-Internal-Token` header. The token is
loaded from `EEVIDENCE_INTERNAL_TOKEN` and rotates quarterly (calendar
reminder in `infra/cron-rotations`).

* `POST /api/v1/legal/eevidence/respond` — close a ticket with an
  `OrderResponse` (provided / partial / refused / no_data).
* `POST /api/v1/legal/eevidence/emergency-mark` — promote an existing ticket to
  emergency, with a free-text justification of at least 12 characters.
* `GET  /api/v1/legal/eevidence/register/open` — JSON list of open tickets;
  feeds the operator dashboard.
* `GET  /api/v1/legal/eevidence/register` — full audit chain + chain validity
  flag; downloaded weekly into the read-only legal archive bucket.

Authority-facing endpoints (no internal token):

* `POST /api/v1/legal/eevidence/submit` — submit an EPOC.
* `POST /api/v1/legal/eevidence/submit/emergency` — submit and immediately
  flag emergency.
* `POST /api/v1/legal/eevidence/submit/preservation` — submit an EPOC-PR.
* `GET  /api/v1/legal/eevidence/ticket/<id>` — status look-up (payload
  redacted on this public-ish path).

## 6. Cron / watchdogs

| Job | Frequency | Action |
|-----|-----------|--------|
| `eevidence_sla_watchdog` | every 5 min | Page DPO when an emergency ticket reaches T-30 min and is not yet `responded` / `refused`. |
| `eevidence_standard_watchdog` | every 1 h | Email DPO + CEO when a standard ticket crosses T-24 h. |
| `eevidence_audit_snapshot` | daily 03:15 UTC | Serialise the audit register to encrypted off-site bucket; verify `verify_chain()`. |
| `eevidence_transparency_export` | bi-annual (1 Feb / 1 Aug) | Aggregate counts per Member State + outcome for the public report. |

## 7. GDPR + retention

* **Order metadata** (issuing authority, case reference, urgency, outcome) — 5
  years after the case file at the issuing authority closes, per typical
  MLAT practice. After that we redact PII but keep statistical aggregates.
* **Target identifiers** — stored as `sha256:<12-char-prefix>` in the audit
  register (see `_redact_payload` in `portal.py`). The plaintext lives only in
  the case-management tool, encrypted at rest and accessible only by the DPO
  and the EU Rep.
* **Disclosed content** — encrypted via the issuing authority's PGP key
  before being uploaded to the response S3 bucket; bucket policy auto-deletes
  the object 30 days after upload.
* **E2EE limit disclosure** — MD-Chat operates an end-to-end-encrypted
  protocol (Signal-pattern + PQXDH). For content requests we can only deliver
  **server-visible metadata**: account creation timestamp, last-seen
  coarse-IP (/24, 6-month retention), federation-server identifier, and
  account-binding email / phone (if present). This limitation is documented
  in every refusal and partial-disclosure response.

## 8. Transparency report

Published bi-annually on `https://md-chat.eu/legal/transparency`. Contents:

* Orders received, by Member State, urgency level, and data category.
* Orders fully complied with, partially complied with, refused, withdrawn.
* Median response time per urgency band.
* Refusal grounds invoked (counts per `RefusalGround`).
* Number of preservation orders received + renewals.
* Number of E2EE-limit disclosures (cases where we could not produce
  content because of architectural limits).

## 9. Blueprint registration TODO

The Flask app factory in `md_chat_ai/api/__init__.py` does **not yet** import
the eEvidence blueprint. Before deploying to staging:

```python
# md_chat_ai/api/__init__.py
from .eevidence import bp as eevidence_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(eevidence_bp, url_prefix="/api")
    return app
```

Also required:

* Add `EEVIDENCE_INTERNAL_TOKEN` to `.env.example` and the Vault root.
* Add Cloudflare WAF rule to rate-limit public submit endpoints (max 10/min
  per source IP).
* Add the operator dashboard route to the SPA in `web/`.
* Add nginx allow-list for the issuing-authority IP ranges where known
  (advisory; we still accept anonymous submissions per Art. 7).

## 10. License

This module and the surrounding code are released under **Apache License
2.0** (SPDX-License-Identifier: `Apache-2.0`), consistent with the rest of
the MD-Chat AI organising layer.
