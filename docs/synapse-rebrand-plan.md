# Synapse Fork Rebrand Plan — MD-Chat

> **Audience:** a developer who has never forked Synapse before.
> **Scope:** end-to-end inventory of every string, asset, template, and config field that must change from Element/Synapse defaults to MD-Chat branding (`msg.md-chat.eu`).
> **Upstream tracked:** `element-hq/synapse` (AGPLv3 community edition, *not* Synapse Pro).
> **Estimated effort:** ~36–48 engineering hours for the first pass + ~6h/quarter to stay current.

---

## 0. Context and ground rules

MD-Chat is a sovereign EU messenger. The transport layer (Layer 1 in `docs/architecture.md`) is a Synapse fork. We do **not** want to vendor a wholesale copy of Synapse into the monorepo — we maintain a thin "branding overlay" plus a small number of patches against a tracked upstream tag.

### Two strategic constraints
1. **AGPLv3** — every Synapse modification we ship binds us to the AGPL. The brand layer is a derivative work; we will release it publicly at `github.com/olegchetrean/md-chat/synapse-fork` once the first deploy goes live.
2. **Synapse Pro vs Synapse Open** — Element introduced **Synapse Pro** (closed source, commercial) in **January 2026**. We track **Synapse Open** (the community AGPLv3 edition at `element-hq/synapse`). Feature-parity gaps are documented in §12.

### Working copy convention
Throughout this document:

| Token | Meaning |
|---|---|
| `$UPSTREAM` | a clean checkout of `element-hq/synapse` at the tracked tag (currently target `v1.121.0` or latest stable at fork time) |
| `$FORK` | our fork checkout (under `github.com/olegchetrean/md-chat-synapse`) |
| `$OVERLAY` | `/Users/macbook_nou/Projects/md-chat/infra/synapse/overlay/` — the brand-only file overlay copied on top of the upstream image at build time |

The overlay pattern (Dockerfile copies files **after** `pip install matrix-synapse`) lets us avoid forking 90% of upstream code. We only fork what cannot be overridden via config or volume mount.

---

## 1. Inventory of paths and files to rebrand

The Synapse repository has the following top-level layout (verified at upstream HEAD):

```
synapse/
├── .github/                # CI/CD — not user-facing, skip
├── changelog.d/            # release notes — skip
├── contrib/                # ops scripts — skip
├── debian/                 # debian packaging — skip
├── demo/                   # demo configs — skip (we use Docker)
├── docker/                 # official Dockerfile — REVIEW (we extend it)
├── docs/                   # mdBook — skip (we publish our own at docs.md-chat.eu)
├── rust/                   # native modules — skip (no branding)
├── synapse/                # the Python package — **patch surface**
│   ├── config/             # config parsing — emailconfig.py, server.py
│   ├── res/templates/      # HTML/TXT email + SSO templates — **largest patch zone**
│   ├── static/             # served HTML — login page, default landing
│   └── (rest)              # core protocol code — DO NOT TOUCH
├── tests/                  # unit + integration — review for hardcoded "Synapse"/"Matrix" assertions
├── README.rst              # heavy Element branding — REWRITE in fork
├── AUTHORS.rst             # contributor list — APPEND (do not replace)
├── CHANGES.md              # upstream changelog — keep + prepend our own
├── LICENSE-AGPL-3.0        # KEEP (mandatory)
├── LICENSE-COMMERCIAL      # DELETE (we don't sell commercial licenses; this is Element's)
└── NOTICE                  # add new file (see §8)
```

### 1.1 The patch surface (12 files / ~28 strings)

These are the *only* files that contain user-visible brand strings. Every other change is config-driven.

| # | Absolute path (relative to `$FORK/`) | Why | Estimated touch |
|---|---|---|---|
| 1 | `synapse/static/index.html` | Default landing page says "It works! Synapse is running" | 1 file, ~20 lines |
| 2 | `synapse/static/client/login/index.html` | Generic but `<title>Login</title>` should say `MD-Chat — Login` | 1 line |
| 3 | `synapse/static/client/login/style.css` | Currently bare; add brand colors | append ~30 lines |
| 4 | `synapse/res/templates/_base.html` | Lines 11–18: hardcoded conditional for `Riot`/`Vector`/`Element` logos | replace `if/elif/else` with single MD-Chat block |
| 5 | `synapse/res/templates/notif_mail.html` | Same `app_name` conditional (~lines 14–20) + `<title>New activity in room</title>` | similar |
| 6 | `synapse/res/templates/notif_mail.txt` | Plaintext footer references Matrix conventions | 2 lines |
| 7 | `synapse/res/templates/mail.css` | Generic — KEEP but add `mail-MDChat.css` sibling | new file ~80 lines |
| 8 | `synapse/res/templates/mail-Element.css` | DELETE (we don't ship Element-themed mail) | — |
| 9 | `synapse/res/templates/mail-Vector.css` | DELETE | — |
| 10 | `synapse/res/templates/sso_redirect_confirm.html` | "Continue to your account" — fine, but add `<title>MD-Chat — Confirm sign-in</title>` | 2 lines |
| 11 | `synapse/res/templates/sso_error.html` | Generic error page — add brand header | 5 lines |
| 12 | `synapse/res/templates/sso_login_idp_picker.html` | "Sign in with…" IdP picker — add brand block | 3 lines |
| 13 | `synapse/res/templates/sso_account_deactivated.html` | Generic deactivation notice — add support contact `support@md-chat.eu` | 2 lines |
| 14 | `synapse/res/templates/sso_new_user_consent.html` | First-login consent — link to `https://md-chat.eu/terms` and `/privacy` | 4 lines |
| 15 | `synapse/res/templates/sso_auth_account_details.html` | Username picker | 1 line title |
| 16 | `synapse/res/templates/registration.html` + `.txt` | "Confirm your email" — replace Matrix/Synapse with MD-Chat | 6 lines across both |
| 17 | `synapse/res/templates/registration_success.html` | Welcome page | 4 lines |
| 18 | `synapse/res/templates/password_reset.html` + `.txt` | Reset email body | 6 lines |
| 19 | `synapse/res/templates/password_reset_confirmation.html` | "Click to confirm" page | 3 lines |
| 20 | `synapse/res/templates/password_reset_success.html` | "Done" page | 3 lines |
| 21 | `synapse/res/templates/account_renewed.html` | Account renewal flow (only if we enable account validity) | 2 lines |
| 22 | `synapse/res/templates/notice_expiry.html` + `.txt` | Account expiry warning | 4 lines |
| 23 | `synapse/res/templates/add_threepid.html` + `.txt` | 3PID (email/phone) verification | 6 lines |

**Total user-facing strings to change: ~28 distinct strings across 22 files.**
Every change can be expressed as `app_name=MD-Chat` config + a string overlay; **no Python source code edits are required for branding alone**.

### 1.2 Hidden Element references in tests

Run from `$UPSTREAM`:
```bash
grep -rnE '"(Riot|Vector|Element)"' tests/
```
Expected hits: `tests/rest/client/test_login.py`, `tests/push/test_email.py` — these test the templating conditional. Our overlay collapses the conditional to a single block, so we patch these tests to assert `MD-Chat` instead. ~8 lines across 3 test files.

---

## 2. Branded strings table — old → new

This is the canonical search-and-replace table. Apply with surgical care; do **not** do a blanket `sed` — several Synapse internals reference "Matrix" as the *protocol* name, which we keep.

| Category | Old | New | Notes |
|---|---|---|---|
| Server FQDN | `matrix.example.com`, `synapse-py-matrix.io`, `example.com` | `msg.md-chat.eu` | Already correct in our `homeserver.yaml` |
| Web baseurl | (default empty) | `https://msg.md-chat.eu` | |
| App name (email `app_name`) | `Matrix` (default), `Element` | `MD-Chat` | Set in `homeserver.yaml` `email.app_name: MD-Chat` |
| Email `notif_from` | unset | `MD-Chat <notif@md-chat.eu>` | |
| Email `riot_base_url` | (Element-only legacy) | `https://app.md-chat.eu` | Used for "Open in app" links |
| Default landing H1 | `It works! Synapse is running` | `MD-Chat msg.md-chat.eu — operational` | `synapse/static/index.html` |
| Default landing body | `Your Synapse server is listening...` | `This is the MD-Chat homeserver. Download the app at md-chat.eu.` | |
| Default landing footer | `Welcome to the Matrix universe :)` | `Operated by Mega Promoting SRL · contact: support@md-chat.eu` | |
| README title | `Element Synapse` | `MD-Chat Server (Synapse fork)` | |
| README header logo | `element-logo.png` | `mdchat-logo.svg` | replace asset under `docs/website_files/` |
| Support link | `element.io/help` | `md-chat.eu/help` | |
| Licensing email | `licensing@element.io` | `legal@md-chat.eu` (we don't sell commercial; keep for inquiries) | |
| Admin contact (ResourceLimitError page) | unset | `mailto:admin@md-chat.eu` | `admin_contact` in homeserver.yaml |
| Default room name on creation | `Empty room` | `Cameră nouă` (RO) / `New room` (EN) — choose i18n branch | |
| Default account display | `@user:msg.md-chat.eu` | unchanged — but UI hides domain on same-homeserver display |
| User agent in federation | `Synapse/1.121.0` | `MD-Chat-Server/1.121.0 (Synapse-derived)` | `synapse/http/__init__.py` SYNAPSE_VERSION usage. **OPTIONAL** — leaks differentiation; recommend keeping default for federation compatibility |
| Server `software` field (`/_matrix/federation/v1/version`) | `Synapse` | `MD-Chat` | one line in `synapse/rest/key/v2/local_key_resource.py` *only if we choose to differentiate*; default = leave as `Synapse` so partner servers don't blocklist us as "unknown" |
| Sender (email From: address) | `synapse@<server_name>` | `MD-Chat <no-reply@md-chat.eu>` | via `email.notif_from` |
| Bot/Server Notices display name | `Server Notices` | `MD-Chat System` | `server_notices.system_mxid_display_name` |

### 2.1 What we deliberately do NOT rebrand

- The string **"Matrix"** when it refers to the protocol (e.g., "this is a Matrix client", `/_matrix/...` URLs). MD-Chat *is* a Matrix server; pretending otherwise breaks federation and confuses developers.
- The string **"Synapse"** inside Python class names, log messages addressed to operators (e.g., `SynapseHomeServer`), and internal metric labels. These are operator-facing and must stay greppable against upstream docs.
- HTTP `Server:` header — leave as default (or strip via nginx). Hiding it triggers security-scanner false positives.

---

## 3. Email templates — line-level rebrand spots

The templates live at `synapse/res/templates/`. Synapse loads them at startup from disk; you can **override individually** by mounting a custom dir via `email.template_dir` in `homeserver.yaml`. **We will use the override mechanism, not patch upstream** — this means our overlay has copies only of templates we change.

Procedure: copy the upstream file into `$OVERLAY/templates/`, edit, and add to `template_dir` config.

### 3.1 `_base.html` — the layout

Upstream lines 11–18 contain a conditional:
```jinja
{% if app_name == "Riot" %}
  <img src="https://riot.im/.../logo.png" />
{% elif app_name == "Vector" %}
  <img src="https://matrix.org/.../logo.png" />
{% elif app_name == "Element" %}
  <img src="https://static.element.io/.../logo.png" />
{% else %}
  <img src="https://matrix.org/.../matrix-logo.png" />
{% endif %}
```

Replace with a single block:
```jinja
<img src="https://md-chat.eu/static/email/mdchat-logo.svg"
     alt="MD-Chat" width="220" />
```
Also change `<link rel="stylesheet" href="mail-{{ app_name }}.css">` to load `mail-MDChat.css`. Asset must be hosted at `https://md-chat.eu/static/email/` with a 10-year cache header.

### 3.2 `notif_mail.html`

Same conditional pattern at the top of `<body>`. Replace with the single block. Additionally:
- Line ~38: `<title>New activity in room {{ ... }}</title>` → `<title>MD-Chat — Activitate nouă în {{ ... }}</title>`
- Footer link to Element → remove

### 3.3 `notif_mail.txt`

Last 3 lines typically reference "Matrix" generally. Replace with:
```
You are receiving this because you have an MD-Chat account.
Manage notifications at https://app.md-chat.eu/#/settings/notifications
Unsubscribe: https://app.md-chat.eu/#/account/email-prefs
```

### 3.4 `registration.html`

Upstream subject line is set in Python (`synapse/handlers/identity.py`) as `"[%(server_name)s] Confirm your email address for Matrix"`. **This requires a code patch**, not just template overlay. See §9 step 5.

Body lines to edit:
- Greeting: `Hi {{ user_id }}` → keep
- Body paragraph: `Click the link below to confirm that this email address is associated with your Matrix account on {{ server_name }}` → `…with your MD-Chat account on {{ server_name }}`
- Button text: `Confirm` → `Confirmă` (RO) / `Confirm` (EN)
- Footer: link to `https://matrix.org/...` → `https://md-chat.eu/help/email-verification`

### 3.5 `password_reset.html`

Body line: `If you didn't ask to reset your password on your Matrix account…` → `…on your MD-Chat account…`.

### 3.6 `add_threepid.html`

`add a new email address / phone number to your Matrix account` → `…to your MD-Chat account`.

### 3.7 Subject line patches (require Python edits)

The following subjects are set in code, not templates. List of files + line areas:

| File | Constant / function | Old subject | New subject |
|---|---|---|---|
| `synapse/handlers/identity.py` | `send_threepid_validation` | `"[%s] Confirm your email address for Matrix"` | `"[%s] Confirmă adresa de email pentru MD-Chat"` |
| `synapse/handlers/identity.py` | `send_password_reset_mail` | `"[%s] Password reset"` | `"[%s] Resetare parolă MD-Chat"` |
| `synapse/push/mailer.py` | `send_notification_mail` | `"[%s] New activity in room"` | `"[%s] Activitate nouă în"` |

Total: 4 Python lines, 1 file each. Trivial patch but **does** create a code fork delta — track via a single `0001-rebrand-email-subjects.patch` file in `$OVERLAY/patches/`.

---

## 4. OAuth / SSO branding

Synapse SSO templates render server-side, so all SSO flows pass through our overlay. The brand touchpoints:

### 4.1 Login screen
- `synapse/static/client/login/index.html` — `<title>Login</title>` → `<title>MD-Chat — Autentificare</title>`. Also the empty `<h1 id="title"></h1>` is filled by JS; we'll inject `MD-Chat` via a small `login.js` patch (3 lines) or, simpler, hardcode the H1 text.
- Add `<link rel="icon" href="https://md-chat.eu/favicon.ico">`.

### 4.2 IdP picker
For MPass (Sprint 6), the OIDC provider config in `homeserver.yaml` accepts an `idp_brand` field that maps to a button icon. Add:
```yaml
oidc_providers:
  - idp_id: mpass
    idp_name: "MPass (EVO)"
    idp_brand: "mpass"        # maps to res/templates/<brand>.svg
    idp_icon: "mxc://msg.md-chat.eu/<media-id>"
    # …
```
- Upload an `mpass.svg` (and any future EU eID provider logos) to local media via Admin API.
- Add `synapse/res/templates/mpass.svg` to overlay (Synapse looks for `<brand>.svg` first, then `idp_icon`).

### 4.3 OIDC error templates
`sso_error.html` defaults to bare text. Overlay it with a branded version that links to `https://md-chat.eu/help/sso-error`.

### 4.4 OAuth consent screen
`sso_new_user_consent.html` is shown on first SSO login. Default text is generic; we replace with text that **explicitly references our ToS at md-chat.eu/terms and Privacy Notice at md-chat.eu/privacy** — required by GDPR Art. 13.

---

## 5. Default room / account name conventions

Synapse has very few hardcoded names — most are empty. The notable ones:

| Setting | Default | MD-Chat value | Where to set |
|---|---|---|---|
| `server_notices.system_mxid_localpart` | `_server` | `_mdchat` | `homeserver.yaml` |
| `server_notices.system_mxid_display_name` | `Server Notices` | `MD-Chat System` | `homeserver.yaml` |
| `server_notices.system_mxid_avatar_url` | unset | `mxc://msg.md-chat.eu/<media-id>` for `mdchat-logo.png` | `homeserver.yaml` |
| `server_notices.room_name` | `Server Notices` | `Anunțuri MD-Chat` | `homeserver.yaml` |
| `server_notices.auto_join` | `false` | `true` (all new users get the room) | `homeserver.yaml` |
| `user_directory.search_all_users` | `false` | `false` (privacy — keep) | confirm in `homeserver.yaml` |
| Default room version | implicit `10` | explicit `11` (MSC3389, supported in v1.117+) | `default_room_version: "11"` |
| `enable_room_list_search` | `true` | `false` initially (closed federation) | `homeserver.yaml` |
| `auto_join_rooms` | `[]` | `["#anunturi:msg.md-chat.eu", "#bun-venit:msg.md-chat.eu"]` | `homeserver.yaml` — see §5.1 |

### 5.1 Auto-joined onboarding rooms

We create two rooms at first deploy:
- `#anunturi:msg.md-chat.eu` — announcement channel, read-only for users
- `#bun-venit:msg.md-chat.eu` — welcome lobby with mini-app pointers

`autocreate_auto_join_rooms: true` must be set. `auto_join_rooms_for_guests: false` (no guest auto-join).

---

## 6. `homeserver.yaml` rebrand-relevant fields — drift audit

Current `/Users/macbook_nou/Projects/md-chat/infra/synapse/homeserver.yaml` is **mostly correct**. Drift items to fix before fork build:

| Field | Current | Required for full rebrand | Severity |
|---|---|---|---|
| `server_name` | `msg.md-chat.eu` | ✓ | OK |
| `public_baseurl` | `https://msg.md-chat.eu` | ✓ | OK |
| `email:` block | **missing entirely** | required for brand emails; see template below | **HIGH** — emails will fall back to `Matrix` defaults |
| `server_notices:` block | **missing** | needs the 5 keys from §5 | HIGH |
| `admin_contact` | **missing** | `mailto:admin@md-chat.eu` | MEDIUM |
| `auto_join_rooms` | **missing** | the 2 rooms from §5.1 | MEDIUM |
| `default_room_version` | unset (= 10) | `"11"` | LOW |
| `enable_room_list_search` | unset (= true) | `false` initially | LOW |
| `templates:` `custom_template_directory` | **missing** | `/data/templates/mdchat/` | **HIGH** — without this, our overlay templates aren't loaded |
| `signing_key_path` | `/data/msg.md-chat.eu.signing.key` | ✓ | OK |
| `report_stats` | `false` | ✓ (we don't ping matrix.org) | OK |

### 6.1 Block to APPEND to homeserver.yaml

```yaml
# --- BRANDING ---
admin_contact: 'mailto:admin@md-chat.eu'

templates:
  custom_template_directory: /data/templates/mdchat/

email:
  smtp_host: smtp.brevo.com
  smtp_port: 587
  smtp_user: ${BREVO_SMTP_USER}
  smtp_pass: ${BREVO_SMTP_PASS}
  require_transport_security: true
  notif_from: "MD-Chat <notif@md-chat.eu>"
  app_name: "MD-Chat"
  enable_notifs: true
  notif_for_new_users: false
  client_base_url: "https://app.md-chat.eu"
  validation_token_lifetime: 1h
  invite_client_location: "https://app.md-chat.eu"

server_notices:
  system_mxid_localpart: _mdchat
  system_mxid_display_name: "MD-Chat System"
  system_mxid_avatar_url: "mxc://msg.md-chat.eu/SET_AFTER_UPLOAD"
  room_name: "Anunțuri MD-Chat"
  auto_join: true

auto_join_rooms:
  - "#anunturi:msg.md-chat.eu"
  - "#bun-venit:msg.md-chat.eu"
autocreate_auto_join_rooms: true
auto_join_rooms_for_guests: false

default_room_version: "11"
enable_room_list_search: false

# Privacy notice URL (shown on consent flows)
user_consent:
  template_dir: /data/templates/mdchat/consent/
  version: "2026.1"
  server_notice_content:
    msgtype: m.text
    body: >-
      Pentru a continua să folosiți MD-Chat, vă rugăm să acceptați
      versiunea actualizată a Termenilor și a Notei de Confidențialitate
      la https://md-chat.eu/terms
  send_server_notice_to_guests: false
  block_events_error: >-
    Trebuie să acceptați Termenii actualizați pentru a trimite mesaje.
    Vedeți https://md-chat.eu/terms
```

---

## 7. Federation listing — where MD-Chat must appear

Matrix has no central registry, but several conventions exist:

| Listing | URL | Action | Priority |
|---|---|---|---|
| `matrix.org` published rooms (room directory) | matrix.org via federation | publish `#bun-venit:msg.md-chat.eu` once stable | P2 |
| `joinmatrix.org` (server directory) | https://joinmatrix.org/ | submit PR adding `msg.md-chat.eu` with description + region tag `EU/Moldova` | P1 |
| `servers.joinmatrix.org` (alternative) | https://servers.joinmatrix.org/ | same as above | P1 |
| `modular.im` / Element Matrix Services fact sheet | (legacy, deprecated 2025) | skip | — |
| `matrix.org` `/_matrix/federation/v1/version` discovery | self-served | ensure `software: Synapse` (default) so partners don't fail unknown-server checks; see §2 | P0 — automatic |
| `.well-known/matrix/server` | https://md-chat.eu/.well-known/matrix/server | **must serve** `{"m.server": "msg.md-chat.eu:443"}` from the apex; nginx config for this is in `infra/nginx/` | P0 |
| `.well-known/matrix/client` | https://md-chat.eu/.well-known/matrix/client | serve `{"m.homeserver": {"base_url": "https://msg.md-chat.eu"}, "m.identity_server": {"base_url": "https://vector.im"}}` (identity server TBD — see Sprint 3) | P0 |
| EU sovereign-stack directory (anticipated 2027 under DMA Art. 7) | TBD | watch for ENISA / EDPB announcements | P3 |
| Maintain a `support` contact via `.well-known/matrix/support` (MSC1929) | https://md-chat.eu/.well-known/matrix/support | serve JSON with `support_page` + `contacts` (DPO, security, admin) | **P0** — required by GDPR + CRA disclosure |

`.well-known/matrix/support` minimal payload:
```json
{
  "contacts": [
    {"role": "m.role.admin",    "email_address": "admin@md-chat.eu", "matrix_id": "@admin:msg.md-chat.eu"},
    {"role": "m.role.security", "email_address": "security@md-chat.eu"}
  ],
  "support_page": "https://md-chat.eu/help"
}
```

---

## 8. License posture: AGPLv3 + NOTICE updates

### 8.1 Files to **keep verbatim** from upstream
- `LICENSE-AGPL-3.0` — keep exactly. Do not modify a single character.
- `AUTHORS.rst` — **append** our names; do not replace.
- All in-file SPDX headers (`# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Element-Commercial`) — keep unless we make a substantive code change to the file.

### 8.2 Files to **delete**
- `LICENSE-COMMERCIAL` — this is Element's commercial license offering. We do not sell commercial Synapse licenses; keeping the file is misleading. Remove it and note in the README.

### 8.3 New file: `NOTICE`
Create `$FORK/NOTICE`:
```
MD-Chat Server
==============

This product includes software developed by Element Hardware (UK) Limited and
the Synapse contributors, originally distributed under the GNU AGPL v3.0 at
https://github.com/element-hq/synapse.

Modifications copyright © 2026 Mega Promoting SRL, Chișinău, Moldova.
Distributed under the GNU AGPL v3.0.

Source code for this server is available at:
  https://github.com/olegchetrean/md-chat-synapse

Operator information and DPO contact:
  https://md-chat.eu/legal
  dpo@megapromoting.com
```

### 8.4 README updates
The fork README must:
1. Open with: `MD-Chat Server is a Matrix homeserver, derived from Element Synapse (AGPLv3).`
2. Link **back** to upstream: `https://github.com/element-hq/synapse`.
3. Acknowledge the original copyright holders inline.
4. State the AGPL Section 13 "Network use" obligation: any user interacting with `msg.md-chat.eu` over the network is entitled to a copy of the corresponding source — link to `https://md-chat.eu/source`.

### 8.5 In-server source disclosure
AGPL §13 requires a link to corresponding source visible to network users. Implementation: serve at `https://md-chat.eu/source` (handled by nginx, not Synapse) and also include the link in our overlay `static/index.html`.

---

## 9. Step-by-step PR-ready patch instructions (<2 hours)

> **Prerequisites:** Docker, git, an editor. The fork lives at `github.com/olegchetrean/md-chat-synapse`.

### Step 1 — Initialize the fork (10 min)
```bash
# work outside the md-chat monorepo
mkdir -p ~/Projects/md-chat-synapse && cd ~/Projects/md-chat-synapse
git clone https://github.com/element-hq/synapse.git .
git remote rename origin upstream
git remote add origin git@github.com:olegchetrean/md-chat-synapse.git
git checkout -b mdchat/main v1.121.0   # pin to a tagged release
```

### Step 2 — Create the overlay structure (5 min)
```bash
mkdir -p overlay/templates overlay/static overlay/patches
```

### Step 3 — Copy the templates we will rebrand (10 min)
```bash
TPL=synapse/res/templates
mkdir -p overlay/templates
cp $TPL/_base.html overlay/templates/
cp $TPL/notif_mail.html overlay/templates/
cp $TPL/notif_mail.txt overlay/templates/
cp $TPL/registration.html overlay/templates/
cp $TPL/registration.txt overlay/templates/
cp $TPL/password_reset.html overlay/templates/
cp $TPL/password_reset.txt overlay/templates/
cp $TPL/add_threepid.html overlay/templates/
cp $TPL/sso_*.html overlay/templates/
cp $TPL/account_renewed.html overlay/templates/
cp $TPL/notice_expiry.html overlay/templates/
cp $TPL/notice_expiry.txt overlay/templates/
```

### Step 4 — Apply template edits (30 min)
Using the line-level guidance from §3, edit each file in `overlay/templates/`. Verify with:
```bash
grep -RinE '(Riot|Vector|Element|Matrix\s+account|matrix\.org)' overlay/templates/
```
Expected: zero hits. (We keep "Matrix" only where it refers to the protocol, e.g., "Matrix client".)

### Step 5 — Patch email subjects in Python (15 min)
```bash
git checkout -b mdchat/email-subjects
# edit synapse/handlers/identity.py and synapse/push/mailer.py per §3.7
git add synapse/handlers/identity.py synapse/push/mailer.py
git commit -m "rebrand: MD-Chat email subjects"
git format-patch -1 -o overlay/patches/
git checkout mdchat/main
git branch -D mdchat/email-subjects
```
The patch is now versioned at `overlay/patches/0001-rebrand-email-subjects.patch` and re-applied on top of each upstream rebase.

### Step 6 — Update README, AUTHORS, NOTICE, delete LICENSE-COMMERCIAL (15 min)
Per §8. Commit on `mdchat/main`.

### Step 7 — Build the branded Docker image (15 min)
Create `overlay/Dockerfile`:
```dockerfile
FROM ghcr.io/element-hq/synapse:v1.121.0
COPY overlay/templates/ /data/templates/mdchat/
COPY overlay/static/    /usr/local/lib/python3.12/site-packages/synapse/static/
COPY overlay/patches/   /tmp/patches/
RUN cd /usr/local/lib/python3.12/site-packages && \
    for p in /tmp/patches/*.patch; do patch -p2 < "$p"; done && \
    rm -rf /tmp/patches
LABEL org.opencontainers.image.source="https://github.com/olegchetrean/md-chat-synapse"
LABEL org.opencontainers.image.licenses="AGPL-3.0-only"
LABEL org.opencontainers.image.title="MD-Chat Server"
LABEL org.opencontainers.image.vendor="Mega Promoting SRL"
```
Build:
```bash
docker build -f overlay/Dockerfile -t ghcr.io/olegchetrean/md-chat-server:0.1.0 .
```

### Step 8 — Wire `template_dir` in `homeserver.yaml` (5 min)
Add the `templates.custom_template_directory: /data/templates/mdchat/` field as shown in §6.1.

### Step 9 — Smoke-test (10 min)
```bash
docker run --rm -e SYNAPSE_SERVER_NAME=msg.md-chat.eu \
  -e SYNAPSE_REPORT_STATS=no \
  ghcr.io/olegchetrean/md-chat-server:0.1.0 generate
docker run --rm -p 8008:8008 -v $(pwd)/data:/data \
  ghcr.io/olegchetrean/md-chat-server:0.1.0
curl -s http://localhost:8008/ | grep -q "MD-Chat" && echo "landing OK"
curl -s http://localhost:8008/_matrix/static/client/login/ | grep -q "MD-Chat" && echo "login OK"
```

### Step 10 — Push and tag (5 min)
```bash
git push origin mdchat/main
git tag mdchat/0.1.0 && git push origin mdchat/0.1.0
```

**Total wall-clock: ~1h45m for a developer following along.**

---

## 10. CI implications — what upstream tests might break

Synapse's CI runs `pytest tests/` and a `complement` Go-based federation test suite. The branding changes touch:

| Test path | Failure mode | Fix |
|---|---|---|
| `tests/push/test_email.py::test_simple_sytest` | Asserts subject `[server] New activity in room` | overlay the test's expected string |
| `tests/push/test_email.py::test_invite_for_user` | Asserts `app_name == "Mail"` default | parameterize or skip |
| `tests/handlers/test_identity.py::test_send_threepid_validation_email` | Asserts subject contains "Matrix" | update expected string |
| `tests/rest/client/test_login.py::test_well_known` | Could be affected if we change `.well-known` path | keep `.well-known` defaults; serve via nginx not Synapse |
| `tests/server.py` log capture | None expected | — |
| `complement/...` federation tests | Should pass — `software` field unchanged | — |

Strategy: maintain a `overlay/patches/0002-test-rebrand-assertions.patch` that updates the ~6 assertions. **Do not delete tests.** Add a CI job in `.github/workflows/build.yml` that runs `pytest tests/push tests/handlers/test_identity.py tests/rest/client/test_login.py` after applying our patches; fail the build if any unexpected breakage appears.

CI changes needed in our fork (`.github/workflows/`):
1. **Build & test** — apply patches, run targeted tests, build Docker image, push to ghcr.io on tag.
2. **Upstream watch** — weekly cron job (`upstream-drift.yml`) that fetches upstream tags and opens an issue if a new tagged release exists. Use `peter-evans/repository-dispatch` to notify Slack/email.
3. **License compliance** — `reuse lint` step ensuring SPDX headers preserved.

---

## 11. Fork health — staying current with upstream Synapse

The hardest part of forking Synapse is **not** the rebrand. It is staying close enough to upstream that you can absorb security fixes within 24h and feature releases within 30 days.

### 11.1 Rebase cadence

**Recommendation: track stable tags, rebase monthly, hot-fix on security advisories.**

| Cadence | Trigger | Action |
|---|---|---|
| Daily (automated) | watch `element-hq/synapse` releases | open PR if new patch tag |
| Weekly (automated) | dependency scanner (Renovate / Dependabot) | minor deps PRs |
| Monthly (manual) | new minor tag (e.g., `v1.122.0`) | rebase `mdchat/main` onto tag, run CI, smoke deploy to staging |
| **Within 24h** | Synapse Security Advisory (GHSA) | hot-fix branch off current `mdchat/main`, cherry-pick CVE patch, emergency deploy |
| Quarterly | major version bump (e.g., room version, DB schema) | full regression sweep, 2-week staging soak |

### 11.2 Rebase vs squash strategy — **rebase**, not squash

Our patch set is tiny (~6 Python lines + ~28 string overlays). Rebasing cleanly on each upstream tag costs ~10 minutes. Squashing into a "MD-Chat changes" megacommit would:
- destroy `git blame` accuracy for upstream code we touched
- make security-patch cherry-picks harder
- obscure license attribution (each commit has SPDX context)

**Workflow:**
```bash
git fetch upstream
git rebase upstream/v1.122.0      # interactive only if conflicts
git push origin mdchat/main --force-with-lease    # only after CI green
```
`--force-with-lease` is safe because nobody else commits to `mdchat/main`.

### 11.3 Dependency drift

Synapse uses `poetry` (`pyproject.toml` + `poetry.lock`). We **do not** modify these files in the fork — that would force us to maintain a parallel lockfile. Instead, any additional Python deps for MD-Chat-specific modules (e.g., MPass connector) live in a **separate** Python package, installed in the Dockerfile via `pip install md-chat-extensions` after Synapse.

### 11.4 Database migration drift

Upstream ships schema migrations under `synapse/storage/schema/`. **Never** fork migrations. If we add tables (e.g., for the MD-Chat audit log), add them in a **module** loaded via `modules:` in homeserver.yaml. Modules can ship their own migrations independently.

### 11.5 Documentation drift watch
- Subscribe RSS: `https://github.com/element-hq/synapse/releases.atom`
- Watch (notifications): `element-hq/synapse-pro-changelog` — Element posts breaking-change advisories that affect Open too
- Monitor `#synapse:matrix.org` and `#synapse-dev:matrix.org` for at-risk APIs

---

## 12. Synapse Pro vs Synapse Open — feature parity gaps

In **January 2026**, Element announced **Synapse Pro** — a closed-source commercial fork of Synapse that includes performance and admin features not available in the AGPLv3 Open edition. **We use Open.**

### 12.1 Confirmed gaps (as of January 2026 announcement)

| Feature | Synapse Pro | Synapse Open (us) | Mitigation |
|---|---|---|---|
| Native sliding sync (MSC3575) optimized | ✓ optimized, sub-100ms cold sync | ✓ baseline (works, slower) | acceptable for <50k users; revisit at scale |
| Dehydrated devices (Olm session offload) | ✓ | ✓ (since v1.119) | none — Open has it |
| Native presence aggregation | ✓ | ✓ but disabled by default for perf | configure carefully |
| Multi-tenant homeserver | Pro-only | not in Open | not needed — we're single-tenant |
| LDAP/SCIM integration | Pro-only | partial (3rd-party module exists) | use `matrix-synapse-ldap3` module |
| Admin GUI ("Element Server Admin") | Pro-only | not in Open | use `synapse-admin` community tool (https://github.com/etkecc/synapse-admin) |
| Sharding workers UI | Pro-only | manual config in Open | acceptable — we have ops know-how |
| Premium telemetry / Element SLA | Pro-only | not in Open | we have our own monitoring (Prometheus + Grafana, in `infra/`) |
| Anti-spam ML model | Pro-only | community modules exist (`mjolnir`, `meowlnir`) | deploy `meowlnir` as a moderation bot — open source, AGPL-compatible |
| Indexed search (large-scale) | Pro-only optimized | Open has basic full-text via Postgres `tsvector` | sufficient for ≤500k messages/day |

### 12.2 Architectural risk

Element has historically dual-licensed Synapse (AGPL **or** commercial). With Synapse Pro siphoning new performance work into a closed branch, the **Open branch may stagnate** on performance over 12–24 months. Mitigation:
- Track community forks: **Conduit** (Rust, AGPL), **Dendrite** (Go, Apache-2.0) as fallback options.
- Plan an architectural review every 6 months — if Synapse Open commits drop below 30/month, evaluate migrating Layer 1 to Conduit (the room-version compatibility surface is the only hard dependency).

### 12.3 What we explicitly do NOT need from Pro

- Multi-tenant — single tenant by design (`msg.md-chat.eu` only)
- Element-branded admin GUI — we run our own (`mdchat-admin`, planned Sprint 9)
- Element SLA — we have our own ops team
- Element's commercial license terms — we are AGPL-pure

---

## 13. Verification checklist (pre-launch)

Before flipping DNS to point users at the fork, run this 12-item sanity sweep:

```bash
# 1. No Element/Riot/Vector strings in user-facing surfaces
grep -RinE '(Element|Riot|Vector)' overlay/templates/ overlay/static/
# expected: empty

# 2. NOTICE file present
test -f NOTICE && echo "OK"

# 3. AGPL preserved
test -f LICENSE-AGPL-3.0 && echo "OK"

# 4. LICENSE-COMMERCIAL removed
test ! -f LICENSE-COMMERCIAL && echo "OK"

# 5. README mentions fork status
grep -q "derived from" README.md && echo "OK"

# 6. .well-known endpoints respond (after deploy)
curl -fs https://md-chat.eu/.well-known/matrix/server | jq -e '."m.server"'
curl -fs https://md-chat.eu/.well-known/matrix/client | jq -e '."m.homeserver".base_url'
curl -fs https://md-chat.eu/.well-known/matrix/support | jq -e '.contacts[0]'

# 7. Federation version reports something sensible
curl -fs https://msg.md-chat.eu/_matrix/federation/v1/version | jq

# 8. Login page shows MD-Chat
curl -fs https://msg.md-chat.eu/_matrix/static/client/login/ | grep -q "MD-Chat"

# 9. Landing page shows MD-Chat
curl -fs https://msg.md-chat.eu/ | grep -q "MD-Chat"

# 10. Email render — trigger a test registration and inspect MIME

# 11. SSO error template branded
curl -fs https://msg.md-chat.eu/_synapse/client/sso/error?error=test | grep -q "MD-Chat"

# 12. AGPL source disclosure resolvable
curl -fsI https://md-chat.eu/source | grep -q "200"
```

---

## 14. References

- Synapse config docs: https://element-hq.github.io/synapse/latest/usage/configuration/config_documentation.html
- Synapse templates docs: https://element-hq.github.io/synapse/latest/templates.html
- Element Synapse repo: https://github.com/element-hq/synapse
- AGPLv3 text: https://www.gnu.org/licenses/agpl-3.0.html
- Matrix server discovery (MSC1929 — support contacts): https://github.com/matrix-org/matrix-spec-proposals/pull/1929
- Synapse-Admin (community admin GUI): https://github.com/etkecc/synapse-admin
- Meowlnir (community moderation): https://github.com/maunium/meowlnir
- Internal: `infra/synapse/homeserver.yaml`, `docs/architecture.md`, `docs/deploy.md`, `docs/compliance.md`
