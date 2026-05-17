# MPass / MSign Integration — MD-Chat

> Status: **draft / awaiting AGE relying-party slot for `WE BUILD`**
> Owner: identity workstream, MD-Chat
> License of the bridge code: Apache 2.0

This document describes how MD-Chat integrates with Moldova's national identity
stack (MPass + MSign), operated by the **Agentia de Guvernare Electronica (AGE)**
and STISC. It covers onboarding, certificate procurement, the SAML SP that talks
to MPass, the OIDC bridge that talks to Synapse and to mobile/web clients, the
MSign SOAP wrapper, the attribute-release policy, and the eIDAS notification
path Moldova is on.

---

## 1. Why a bridge

* **MPass** only speaks SAML 2.0 (Web Browser SSO profile, HTTP-Redirect +
  HTTP-POST bindings). The IdP metadata is published at
  `https://mpass.gov.md/Metadata`.
* **Synapse** and most modern relying parties (mobile apps, browser clients,
  embedded WebViews) speak OpenID Connect, not SAML.
* Re-implementing SAML in Synapse is out of scope, and embedding `python3-saml`
  inside Synapse would entangle two upstreams.
* Therefore MD-Chat ships a thin **SAML SP → OIDC OP bridge** (this package)
  that:
  1. acts as a SAML 2.0 Service Provider toward MPass;
  2. exposes OIDC discovery, authorize, token, userinfo and JWKS endpoints to
     downstream clients;
  3. enforces a strict attribute-release policy with data minimization at the
     boundary.

The bridge is a separate process inside the `md-chat-ai` Flask app, mounted
under `/api/v1/identity/...` plus the root `/.well-known/openid-configuration`
and `/oidc/...` paths.

---

## 2. Onboarding with AGE (relying-party registration)

> AGE is the **only** entity that can register a relying party in MPass.
> Registration in production requires a signed contract and a registered legal
> entity in Moldova. `WE BUILD` is our current relying-party slot request.

Onboarding sequence:

1. **Submit relying-party request** to AGE (form `mpass-rp-001`, in Romanian).
   Required fields:
    * legal name (MEGA PROMOTING SRL),
    * IDNO,
    * service entity ID (`https://msg.md-chat.eu/saml/sp`),
    * ACS URL (`https://msg.md-chat.eu/api/v1/identity/saml/acs`),
    * SLO URL (`https://msg.md-chat.eu/api/v1/identity/saml/slo`),
    * intended attributes & justification (see §5),
    * data protection officer (DPO) contact,
    * date of intended go-live.
2. **AGE legal review** — typically 10–20 business days. They check that the
   relying party has a lawful basis (Reg. MD 195/2024 + GDPR Art 6).
3. **STISC certificate procurement** — the SP signing/encryption certificate is
   issued by STISC. Form `stisc-cert-002`. Two artefacts:
    * X.509 cert (RSA 2048+, SHA-256),
    * matching private key (kept on the SP, not given to AGE).
4. **Staging onboarding** — AGE provisions the entry in *MPass-pretest* and
   shares an IdP metadata URL for that environment. We push the SP metadata
   (the JSON dump at `/api/v1/identity/saml/metadata` and an XML rendering) to
   AGE.
5. **Conformance tests** — AGE runs a test plan against the SP (signature
   verification, attribute release, SLO, RelayState handling).
6. **Production onboarding** — AGE moves the RP into MPass-prod. They publish
   the production IdP entityID in the metadata URL.
7. **Monitoring** — AGE requires a 24/7 contact and a `security.txt` published
   under the SP domain.

### 2.1 Materials required from MD-Chat side

| Artefact | Owner | Location |
|---|---|---|
| SP entity ID | infra | `MPASS_SP_ENTITY_ID` env var |
| SP cert (PEM) | infra | `/etc/md-chat/mpass/sp.crt` |
| SP private key | infra | `/etc/md-chat/mpass/sp.key` (mode 0400, never in git) |
| Production IdP metadata URL | AGE | `MPASS_IDP_METADATA_URL` env var |
| OIDC signing key (RS256) | infra | `/etc/md-chat/oidc/signing.pem` |
| OIDC discovery URL | bridge | `https://msg.md-chat.eu/.well-known/openid-configuration` |

---

## 3. Certificates — procurement & rotation via STISC

* **CA**: STISC operates the qualified CA for the Moldovan public sector.
* **Form**: `stisc-cert-002`, submitted with the AGE RP request.
* **Algorithm**: RSA-2048+, signed with SHA-256. ECDSA is not yet accepted by
  MPass for SP signing.
* **Validity**: 2 years. Renewal must start 60 days before expiry; AGE rotates
  the published metadata on our behalf so RP downtime is zero if we hand them
  the new cert on time.
* **Storage**: SP private key lives on the SP host only, mode `0400`, owned by
  the `md-chat-ai` UNIX user. Never committed.
* **Rotation log**: every cert rotation is recorded in `docs/compliance.md`
  with the SHA-256 fingerprint of the new and old certs.

---

## 4. Attributes available from MPass

MPass releases a fixed catalogue of attributes; the actual set returned depends
on the user's consent at the IdP. Friendly names:

| SAML attribute | Type | Notes |
|---|---|---|
| `verified` | bool | "true" iff the user authenticated with an identity-verified credential (any LOA ≥ 2). |
| `birth_year` | int | Year only — used to derive `age_band`. |
| `given_name` | string | First name(s). |
| `family_name` | string | Surname(s). |
| `email` | string | Optional; user may withhold. |
| `phone` | string | Optional. |
| `unique_identifier_personal_code` | string | **IDNP — sensitive.** Pseudonymized handle of the citizen; treated as a special-category identifier under MD law and as a "national identifier" under GDPR Art 87. |

MPass also returns `AuthnContextClassRef`, which carries the LOA token
(`LOA1` / `LOA2` / `LOA3`).

---

## 5. Attribute-release policy (data minimization)

The bridge applies an *outbound* filter, before any attribute leaves SAML for
OIDC. Two profiles are supported:

### 5.1 Default profile — `chat_account_provisioning`

Released to OIDC: `verified`, `age_band` (derived from `birth_year`), `prenume`
(from `given_name`), plus standard OIDC envelope (`sub`, `iss`, `aud`, `iat`,
`exp`, `acr`).

**Refused: `unique_identifier_personal_code` (IDNP).** Rationale:

* **GDPR Art 5(1)(c) — data minimization.** Account provisioning in a
  messenger does not need a national identifier.
* **Legea RM 195/2024** (in force 23 August 2026) classifies IDNP as a
  sensitive identifier; processing requires a documented purpose and consent.
* **EU AI Act §50** (mention disclosure) is satisfied without IDNP — we only
  need the chatbot-vs-human marker, not personal IDs.
* Storing IDNP behind a chat handle would create a unique linkage between a
  pseudonymous chat persona and the user's tax / criminal / health records held
  by other state databases — a textbook excessive-processing risk.

`birth_year` is mapped to a coarse `age_band` (`<18`, `18-25`, `26-35`,
`36-45`, `46-55`, `56-65`, `65+`). The exact year never leaves the bridge.

### 5.2 Elevated profile — `msign_qualified_signature`

When the user initiates an MSign flow, the relying party may request the
`idnp` scope. The bridge will:

1. verify the RP is registered with `allow_idnp = True` (a property granted
   only after a separate AGE review);
2. surface the IDNP in the OIDC `idnp` claim of *that single token*;
3. log the release with the `purpose` token (always
   `msign_qualified_signature`) and the relying party's `client_id` for the
   GDPR Art 30 record-of-processing log.

A user who declines this second consent at MPass simply does not get the IDNP
attribute — the SP never falls back to "ask for less" silently.

### 5.3 SAML → OIDC claim map (canonical)

| SAML | OIDC | Notes |
|---|---|---|
| `verified` | `verified` | boolean |
| `birth_year` | `age_band` | string, coarse bucket |
| `given_name` | `prenume` | string |
| `unique_identifier_personal_code` | `idnp` | string, only via elevated profile |
| `AuthnContextClassRef` (`LOA1`/`LOA2`/`LOA3`) | `acr` | `md.gov.mpass.loa1` / `loa2` / `loa3` |
| SAML `NameID` (persistent) | `sub` | opaque, MPass-internal pseudonymous identifier |

The OIDC `sub` is always the MPass `NameID`, never the IDNP — this lets MD-Chat
retire the MPass linkage in the future without leaking a stable
government identifier downstream.

---

## 6. LOA → OIDC `acr` mapping

| MPass LOA | `acr` value | Typical credential |
|---|---|---|
| LOA1 | `md.gov.mpass.loa1` | username + password |
| LOA2 | `md.gov.mpass.loa2` | SMS OTP / mobile-eID |
| LOA3 | `md.gov.mpass.loa3` | USB token, qualified certificate |

Unknown / missing LOA collapses to LOA1 (we never silently *upgrade* trust).

Relying parties can express a minimum required LOA via the OIDC `acr_values`
parameter — the bridge passes that to MPass as a `RequestedAuthnContext`.

---

## 7. MSign — qualified electronic signatures

MSign is a separate AGE-operated SOAP service for producing qualified signatures
on PDFs (EU eIDAS-aspiring, but not yet eIDAS-notified — see §8).

The bridge exposes a REST facade:

```
POST /api/v1/identity/msign/sign
Content-Type: application/json

{
  "document_b64": "<base64 PDF bytes>",
  "mime_type":    "application/pdf"
}
```

Response:

```
200 OK
{
  "signature_id": "sig-…",
  "signed_document_b64": "<base64 signed PDF>",
  "certificate_chain": ["<PEM>", "<PEM>"]
}
```

Internally the wrapper:
1. validates the request (size, MIME type),
2. resolves the user's IDNP via the elevated OIDC profile (which the caller
   must have obtained beforehand),
3. submits a SOAP `Sign` operation to the WSDL at `MSIGN_WSDL_URL`,
4. parses the response (PascalCase or snake_case — robust to MSign revisions),
5. returns the signed bytes.

The WSDL URL, MSign client ID and shared secret are loaded from env vars
(`MSIGN_WSDL_URL`, `MSIGN_CLIENT_ID`, `MSIGN_CLIENT_SECRET`).

---

## 8. eIDAS notification path

Moldova has applied for an Association Agreement-based eIDAS notification of
MPass. As of May 2026 the file is **not yet notified**, so signatures and
authentications produced by MPass / MSign are **not** automatically recognized
as eIDAS-qualified across the EU. Practical consequences:

* Within MD: MSign signatures are legally equivalent to handwritten signatures.
* Within EU: signatures are recognized as advanced electronic signatures
  (AdES) but **not** as QES until notification completes.
* MD-Chat surfaces this in the UI before any MSign-backed action ("This
  signature is qualified in Moldova; outside MD it has AdES status only").

When notification completes we will:
1. update the discovery document `acr` semantics,
2. update this document and `docs/compliance.md`,
3. flip the in-product disclaimer.

---

## 9. Endpoints in this implementation

| Method & path | Purpose |
|---|---|
| `GET /.well-known/openid-configuration` | OIDC discovery |
| `GET /oidc/jwks.json` | RS256 public key set |
| `GET /oidc/authorize` | OIDC authorize endpoint — issues a SAML redirect |
| `POST /oidc/token` | OIDC token endpoint — exchanges code for ID token |
| `GET /oidc/userinfo` | OIDC userinfo — returns minimized claim set |
| `POST /api/v1/identity/saml/acs` | SAML AssertionConsumerService |
| `GET /api/v1/identity/saml/metadata` | SP metadata (JSON dump) |
| `POST /api/v1/identity/msign/sign` | REST wrapper around MSign |

All endpoints return JSON except `/oidc/authorize` and `/oidc/saml/acs`, which
return 302 redirects to follow the SAML browser-SSO profile.

---

## 10. Operational notes

* **Dependencies**: `python3-saml`, `zeep`, `pyjwt[crypto]`. These are gated
  behind the optional `identity` extra in `pyproject.toml` because
  `python3-saml` requires `libxmlsec1` which doesn't install cleanly on every
  workstation. Production images pin the extra.
* **Code & token storage**: the reference implementation keeps OIDC
  authorization codes and access tokens in process memory. Production must
  replace these with Redis-backed maps (the bridge exposes `.codes` and
  `.tokens` as mutable mappings to make this swap trivial).
* **Key management**: the SAML SP key and OIDC signing key are read from disk
  at app boot. Rotate via a rolling restart; old kids stay published in JWKS
  for `id_token_ttl + skew` so in-flight tokens still verify.
* **Audit**: every IDNP release is logged with `client_id`, `purpose`, and an
  opaque `sub`. Logs feed the GDPR Art 30 record-of-processing index.

---

## 11. Open dependencies / blockers

| Item | Owner | Blocker for |
|---|---|---|
| AGE relying-party slot `WE BUILD` approval | AGE legal | All production traffic |
| STISC SP certificate procurement | STISC | SAML signing |
| Pre-test IdP metadata URL | AGE | Conformance tests |
| `allow_idnp=true` review of MSign relying party | AGE | MSign flows |
| Internal DPIA on `idnp` release | MD-Chat DPO | Production go-live with MSign |
| eIDAS notification of MPass | Govt MD | Cross-border QES recognition |

Until AGE approves `WE BUILD`, the bridge runs only against the public MPass
metadata (read-only) and against fake assertions in test. No production
traffic flows.

---

## 12. References

* Reg. MD 195/2024 — Identification electronics, in force 23 Aug 2026.
* GDPR Reg. 2016/679 — Art 5(1)(c), Art 30, Art 87.
* EU AI Act Reg. 2024/1689 — §50 (mention disclosure).
* OASIS SAML 2.0 Core (`saml-core-2.0-os`).
* OIDC Core 1.0 + Discovery 1.0 + JWT (RFC 7519) + PKCE (RFC 7636).
* AGE integration handbook v1.2 (internal; PDF in `infra/docs/age-handbook.pdf`).
