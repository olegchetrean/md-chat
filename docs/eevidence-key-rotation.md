# eEvidence Audit Log — Key Rotation Runbook

**Owner:** DPO + Platform engineering
**Scope:** Ed25519 keys used to sign every entry of the eEvidence audit register (`src/md_chat_ai/eevidence/audit.py` chain, wrapped by `signing.py`).
**Why it matters:** A third-party auditor — or a court receiving a sealed eEvidence bundle under Reg. (EU) 2023/1543 Art. 31 + GDPR Art. 33(5) — must be able to verify chain integrity **without trusting our infrastructure**. The Ed25519 signatures make that possible. If the private key leaks, the trust chain is broken; we must rotate.

## 1. Threat model

We sign every audit entry with `Ed25519` (RFC 8032). The private key lives on the production AI-layer host at `/etc/md-chat/audit/audit-1.pem`, mode `0600`, owner `md-chat:md-chat`. The corresponding public key (kid `mpass-audit-1`) is published as a JWK at `/.well-known/jwks-audit.json` and recorded in the DPIA appendix.

Rotation is mandatory in the following scenarios:

| Trigger | SLA to rotate |
| --- | --- |
| Suspected key leak (host compromise, lost backup, leaked secret in CI logs) | 4 hours |
| Departing sysadmin with key access | 24 hours |
| Scheduled hygiene rotation | every 12 months |
| Algorithm deprecation by IETF / ENISA | per advisory window |
| Court request for fresh key (rare) | 48 hours |

## 2. Key identifiers (`kid`)

Each key has a stable `kid` of the form `mpass-audit-N` where `N` is monotonically increasing. Once minted, a `kid` is **never** re-used — even after the key is destroyed. This guarantees that a verifier reading a 10-year-old archive can look up the right public key unambiguously.

Active kids as of the last audit:

- `mpass-audit-1` — initial key, generated 2026-05-18, **active**.

## 3. Generation procedure (new key)

Run on a host that will host the new key (not on a developer laptop unless this is a dev key):

```bash
sudo -u md-chat /opt/md-chat/ai-layer/.venv/bin/python \
    /opt/md-chat/ai-layer/scripts/generate-audit-key.py \
    /etc/md-chat/audit/audit-2.pem \
    --kid mpass-audit-2
```

Verify the output:

```bash
stat -c '%a %U:%G %n' /etc/md-chat/audit/audit-2.pem
# expected: 600 md-chat:md-chat /etc/md-chat/audit/audit-2.pem
```

The command also prints the JWK to stdout. Capture it:

```bash
sudo -u md-chat /opt/md-chat/ai-layer/.venv/bin/python \
    /opt/md-chat/ai-layer/scripts/generate-audit-key.py \
    /etc/md-chat/audit/audit-2.pem --kid mpass-audit-2 \
    > /etc/md-chat/audit/audit-2.jwk.json
```

## 4. Rotation procedure (zero-downtime)

The `KeyStore.rotate()` method keeps the retired key as **verify-only** so all historical signatures stay valid; only new signatures use the freshly-promoted kid.

1. Generate the new key (section 3).
2. Update the deployment config:
   ```ini
   AUDIT_SIGNING_KEY_PATH=/etc/md-chat/audit/audit-2.pem
   AUDIT_SIGNING_KID=mpass-audit-2
   ```
3. SIGHUP / restart the AI layer:
   ```bash
   sudo systemctl restart md-chat-ai
   ```
4. Publish the new JWK alongside the old one in `/.well-known/jwks-audit.json`. Both kids must be present until everyone who archives bundles has updated their copies (90 days).
5. Smoke-check: emit one event from a synthetic ticket and verify with the **previous** kid's public key still rejects it (it should — the new entry is signed with `mpass-audit-2`).
6. Record the rotation in the breach-response log (`docs/breach-response.md`) with reason code:
   - `R-LEAK` — suspected compromise.
   - `R-HYG`  — scheduled rotation.
   - `R-DEP`  — departing personnel.
   - `R-ALG`  — algorithm deprecation.
7. Destroy the old private key **only after** at least 90 days of overlap and only if no live archive depends on signing more entries with it. The public key stays in `KeyStore` forever.

## 5. Verifying an archived bundle (auditor side)

A court or auditor receives:

- the audit chain (newline-delimited JSON, one entry per line),
- the JWS for each entry (separate file or embedded `jws` field),
- the JWKS file with the historical public keys.

Verification reference (Python, no MD-Chat code required):

```python
import json, base64, jwt
from cryptography.hazmat.primitives.serialization import load_pem_public_key

jwks = json.load(open("jwks-audit.json"))
keys = {k["kid"]: k for k in jwks["keys"]}

for line in open("audit-2026.jsonl"):
    record = json.loads(line)
    jws = record["jws"]
    kid = json.loads(base64.urlsafe_b64decode(jws.split(".")[0] + "=="))["kid"]
    jwk = keys[kid]
    # pyjwt accepts JWK dicts directly via jwt.PyJWK
    pyjwk = jwt.PyJWK(jwk)
    payload = jwt.decode(jws, key=pyjwk.key, algorithms=["EdDSA"])
    assert payload["sha256_chain_hash"] == record["entry"]["entry_hash"]
```

The MD-Chat-provided verifier (`md_chat_ai.eevidence.signing.verify_jws`) does the same thing plus the chain-hash recomputation and the canonical-JSON tamper check.

## 6. Disaster recovery

If the **only** copy of the active private key is lost:

1. The audit register continues to work — entries are still hash-chained.
2. New entries **cannot be signed** until a new key is provisioned.
3. Generate a new key, register it as `mpass-audit-N+1`, restart the service.
4. Publish the new JWK and a signed (by the new key) attestation that explains the gap and references the breach-response ticket.
5. Notify CNPDCP within 72 hours per GDPR Art. 33 — loss of the signing key is a confidentiality + integrity incident affecting evidence destined for criminal proceedings.

Backups: an offline **paper-printed QR** copy of every retired private key is stored at the registered office in a sealed envelope opened only on DPO + CEO joint authorization. Encrypted disk copies live in two geographically separated safes (Chișinău + Bucharest). These backups exist for *historical re-verification* only — they MUST NOT be used to sign new entries.

## 7. Configuration reference

`src/md_chat_ai/config.py` exposes the two settings the runtime consumes:

- `audit_signing_key_path` (env `AUDIT_SIGNING_KEY_PATH`) — absolute path to the active PEM file. Default: `/etc/md-chat/audit/audit-1.pem`.
- `audit_signing_kid` (env `AUDIT_SIGNING_KID`) — kid string written into every JWS header. Default: `mpass-audit-1`.

Old kids are loaded into the `KeyStore` from `/etc/md-chat/audit/retired/*.pem` automatically at startup; their kids are derived from the filename (`audit-N.pem` → `mpass-audit-N`).

## 8. Change history

| Date | kid promoted to active | Reason | Operator | Breach ticket |
| --- | --- | --- | --- | --- |
| 2026-05-18 | `mpass-audit-1` | initial bootstrap | platform-ops | — |
