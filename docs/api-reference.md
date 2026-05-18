# MD-Chat AI Layer — API Reference

Source of truth: [`ai-layer/openapi.yaml`](../ai-layer/openapi.yaml) (OpenAPI 3.1).

Servers:

- **Production:** `https://msg.md-chat.eu`
- **Local dev:** `http://localhost:5002`

## Authentication

| Scheme | Where | Used by |
|---|---|---|
| `BearerAuth` (`Authorization: Bearer <token>`) | HTTP header | `GET /oidc/userinfo` |
| `InternalToken` (`X-MDChat-Internal-Token: <secret>`) | HTTP header | All operator-only eEvidence endpoints |

The internal token is validated with `hmac.compare_digest` against the
`EEVIDENCE_INTERNAL_TOKEN` environment variable. When that variable is
empty the server returns `503 internal_token_not_configured`.

## Error envelope

Every error response uses the same shape:

```json
{"ok": false, "error": "error_code", "details": {}}
```

Tickets and eEvidence endpoints use the legacy shape `{"error": "code", "message": "..."}`
where Pydantic validation produces `details` arrays — both are compatible with
the `Error` schema documented in OpenAPI.

## Endpoint summary

| # | Method | Path | Auth | Tag |
|---|---|---|---|---|
| 1 | GET | `/api/health` | — | health |
| 2 | GET | `/api/ready` | — | health |
| 3 | POST | `/api/v1/auth/phone/send-code` | — | auth |
| 4 | POST | `/api/v1/auth/phone/verify` | — | auth |
| 5 | POST | `/api/v1/auth/mfa/setup` | — | auth |
| 6 | POST | `/api/v1/auth/mfa/verify` | — | auth |
| 7 | POST | `/api/v1/auth/pin/setup` | — | auth |
| 8 | POST | `/api/v1/auth/pin/recover` | — | auth |
| 9 | GET | `/api/v1/identity/saml/metadata` | — | identity |
| 10 | POST | `/api/v1/identity/saml/acs` | — | identity |
| 11 | POST | `/api/v1/identity/msign/sign` | — | identity |
| 12 | POST | `/api/v1/legal/eevidence/submit` | — | eevidence |
| 13 | POST | `/api/v1/legal/eevidence/submit/emergency` | — | eevidence |
| 14 | POST | `/api/v1/legal/eevidence/submit/preservation` | — | eevidence |
| 15 | GET | `/api/v1/legal/eevidence/ticket/{ticket_id}` | — | eevidence |
| 16 | POST | `/api/v1/legal/eevidence/respond` | `X-MDChat-Internal-Token` | eevidence |
| 17 | POST | `/api/v1/legal/eevidence/emergency-mark` | `X-MDChat-Internal-Token` | eevidence |
| 18 | GET | `/api/v1/legal/eevidence/register/open` | `X-MDChat-Internal-Token` | eevidence |
| 19 | GET | `/api/v1/legal/eevidence/register` | `X-MDChat-Internal-Token` | eevidence |
| 20 | GET | `/.well-known/openid-configuration` | — | oidc |
| 21 | GET | `/oidc/jwks.json` | — | oidc |
| 22 | GET | `/oidc/authorize` | — | oidc |
| 23 | POST | `/oidc/token` | — | oidc |
| 24 | GET | `/oidc/userinfo` | Bearer | oidc |

Total: **24 documented endpoints + 1 templated path** (`ticket/{ticket_id}`) =
**25 routes** matching the mounted Flask routemap.

---

## health

### `GET /api/health`

Liveness probe. Returns a static healthy response — no downstream checks.

```bash
curl -s https://msg.md-chat.eu/api/health
```

### `GET /api/ready`

Readiness probe. Returns `503 {ready:false, reason:"config_incomplete"}` if
`NEO4J_PASSWORD`, `ROUTER_API_KEY`, or `INFOBIP_API_KEY` are missing.

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5002/api/ready
```

---

## auth

All auth endpoints accept `application/json`. PII is Argon2id-hashed before
persistence and is never logged.

### `POST /api/v1/auth/phone/send-code`

```bash
curl -X POST https://msg.md-chat.eu/api/v1/auth/phone/send-code \
  -H 'Content-Type: application/json' \
  -H 'Accept-Language: ro' \
  -d '{"phone_number":"79123456","country_code":"MD","user_id":"6f1a8e64-9b9c-4f24-9a86-2b8d1c4d5e6f"}'
```

Errors: `400 missing_fields`, `429 cooldown_active` (includes `cooldown_until`).

### `POST /api/v1/auth/phone/verify`

```bash
curl -X POST https://msg.md-chat.eu/api/v1/auth/phone/verify \
  -H 'Content-Type: application/json' \
  -d '{"code":"482103","user_id":"6f1a8e64-9b9c-4f24-9a86-2b8d1c4d5e6f"}'
```

Errors: `400 invalid_code`, `429 too_many_attempts` (locked after 5 failures).

### `POST /api/v1/auth/mfa/setup`

```bash
curl -X POST https://msg.md-chat.eu/api/v1/auth/mfa/setup \
  -H 'Content-Type: application/json' \
  -d '{"account_name":"oleg@md-chat.eu"}'
```

Returns `qr_uri`, `secret`, 10 plaintext `backup_codes`, and Argon2id
`backup_hashes` to persist. The plaintext codes are returned **once**.

### `POST /api/v1/auth/mfa/verify`

```bash
curl -X POST https://msg.md-chat.eu/api/v1/auth/mfa/verify \
  -H 'Content-Type: application/json' \
  -d '{"secret":"JBSWY3DPEHPK3PXP","code":"482103"}'
```

Pass `backup_hashes` to also accept any unused backup code. Response includes
`method: "totp" | "backup"` and `remaining_hashes` when a backup code is
consumed.

### `POST /api/v1/auth/pin/setup`

Signal-SVR3-pattern stub. Wraps the supplied identity-key blob with the PIN
(Argon2id KDF → AES-256-GCM). Server stores only ciphertext + nonce + salt.

```bash
curl -X POST https://msg.md-chat.eu/api/v1/auth/pin/setup \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"6f1a8e64-9b9c-4f24-9a86-2b8d1c4d5e6f",
    "pin":"183927",
    "wrapped_keys_b64":"QkFTRTY0RU5DT0RFRA=="
  }'
```

### `POST /api/v1/auth/pin/recover`

```bash
curl -X POST https://msg.md-chat.eu/api/v1/auth/pin/recover \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"6f1a8e64-9b9c-4f24-9a86-2b8d1c4d5e6f","pin":"183927"}'
```

Errors: `401 invalid_pin`, `404 not_found`.

---

## identity

### `GET /api/v1/identity/saml/metadata`

JSON view of the SP settings — handy for ops dashboards. For the XML
metadata consumed by the MPass IdP, ask ops for the published URL.

```bash
curl -s https://msg.md-chat.eu/api/v1/identity/saml/metadata
```

### `POST /api/v1/identity/saml/acs`

Form-encoded SAML AssertionConsumerService. Translates an MPass assertion
into an OIDC authorization code, then 302-redirects to the RP.

```bash
curl -i -X POST https://msg.md-chat.eu/api/v1/identity/saml/acs \
  -d 'SAMLResponse=PHNhbWxwOlJlc3BvbnNl...' \
  -d 'RelayState=opaque-token-from-authorize'
```

### `POST /api/v1/identity/msign/sign`

REST facade over the MSign SOAP service (qualified electronic signature).

```bash
curl -X POST https://msg.md-chat.eu/api/v1/identity/msign/sign \
  -H 'Content-Type: application/json' \
  -d '{"document_b64":"JVBERi0xLjQK...","mime_type":"application/pdf"}'
```

Errors: `400` missing/invalid base64, `502 msign_failure` from upstream.

---

## eevidence (EU Reg 2023/1543)

Public endpoints sit behind Cloudflare + WAF. Operator endpoints require
`X-MDChat-Internal-Token`.

### `POST /api/v1/legal/eevidence/submit`

```bash
curl -X POST https://msg.md-chat.eu/api/v1/legal/eevidence/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "case_reference":"RO/PCA/2026/00123",
    "issuing_authority_id":"RO-PCA-BUC",
    "contact_email":"prosecutor@pca.ro",
    "data_categories":["subscriber"],
    "urgency_level":"standard",
    "legal_basis":"Reg 2023/1543 Art 5",
    "deadline_iso":"2026-05-28T00:00:00Z",
    "target_user_id":"tu_9988"
  }'
```

Returns `201 {ticket: {...}}` or `422` validation failure.

### `POST /api/v1/legal/eevidence/submit/emergency`

Same payload — server forces `urgency_level=emergency` and starts the
8-hour SLA timer.

### `POST /api/v1/legal/eevidence/submit/preservation`

EPOC-PR (Art. 9). Requires `target_user_id` + optional `preservation_until`.

### `GET /api/v1/legal/eevidence/ticket/{ticket_id}`

Sanitised view; the original `payload` is stripped to avoid case-detail leakage.

```bash
curl -s https://msg.md-chat.eu/api/v1/legal/eevidence/ticket/1f1f7d18-a04e-4f24-9a86-2b8d1c4d5e6f
```

### `POST /api/v1/legal/eevidence/respond` *(operator)*

```bash
curl -X POST https://msg.md-chat.eu/api/v1/legal/eevidence/respond \
  -H 'Content-Type: application/json' \
  -H "X-MDChat-Internal-Token: $EEVIDENCE_INTERNAL_TOKEN" \
  -d '{
    "ticket_id":"1f1f7d18-a04e-4f24-9a86-2b8d1c4d5e6f",
    "response":{"outcome":"produced","notes":"subscriber data delivered"}
  }'
```

Errors: `401 unauthorized`, `404 not_found`, `409 conflict`, `422` validation.

### `POST /api/v1/legal/eevidence/emergency-mark` *(operator)*

```bash
curl -X POST https://msg.md-chat.eu/api/v1/legal/eevidence/emergency-mark \
  -H 'Content-Type: application/json' \
  -H "X-MDChat-Internal-Token: $EEVIDENCE_INTERNAL_TOKEN" \
  -d '{"ticket_id":"1f1f7d18-...","justification":"Imminent threat — Art. 5(8)"}'
```

### `GET /api/v1/legal/eevidence/register/open` *(operator)*

```bash
curl -s -H "X-MDChat-Internal-Token: $EEVIDENCE_INTERNAL_TOKEN" \
  https://msg.md-chat.eu/api/v1/legal/eevidence/register/open
```

### `GET /api/v1/legal/eevidence/register` *(operator)*

Returns the entire hash-chained audit log plus a `chain_valid` boolean.

```bash
curl -s -H "X-MDChat-Internal-Token: $EEVIDENCE_INTERNAL_TOKEN" \
  https://msg.md-chat.eu/api/v1/legal/eevidence/register
```

---

## oidc

### `GET /.well-known/openid-configuration`

Standard OIDC discovery document.

```bash
curl -s https://msg.md-chat.eu/.well-known/openid-configuration | jq
```

### `GET /oidc/jwks.json`

JWKS for ID-token verification.

```bash
curl -s https://msg.md-chat.eu/oidc/jwks.json | jq
```

### `GET /oidc/authorize`

Begins the OIDC code flow + PKCE; redirects to the MPass IdP.

```bash
open "https://msg.md-chat.eu/oidc/authorize?\
client_id=app.md-chat.eu&\
redirect_uri=https://app.md-chat.eu/cb&\
scope=openid+profile+email&\
state=xyz&nonce=abc&\
code_challenge=...&code_challenge_method=S256"
```

The `idnp` scope additionally requests the Moldovan personal identification
number (subject to user consent at the IdP).

### `POST /oidc/token`

```bash
curl -X POST https://msg.md-chat.eu/oidc/token \
  -d 'grant_type=authorization_code' \
  -d 'code=abc123' \
  -d 'client_id=app.md-chat.eu' \
  -d 'redirect_uri=https://app.md-chat.eu/cb' \
  -d 'code_verifier=...'
```

### `GET /oidc/userinfo` *(Bearer)*

```bash
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://msg.md-chat.eu/oidc/userinfo
```

Errors: `401 invalid_request` (missing header), `401 invalid_token` (expired).

---

## Local Swagger UI

```bash
cd ai-layer
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/serve-swagger-ui.py
# open http://localhost:5050
```

## Validating the spec

```bash
pytest tests/test_openapi_spec.py -v
```

The test uses `openapi-spec-validator` to confirm the YAML parses cleanly
and conforms to OpenAPI 3.1.
