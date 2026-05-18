# md-chat-ios — Element X iOS fork shell

> Sovereign EU messenger client for the MD-Chat platform.
> Derivative work of [`element-hq/element-x-ios`](https://github.com/element-hq/element-x-ios) (AGPLv3).
> Default homeserver: `https://msg.md-chat.eu`.
> Operator: **MEGA PROMOTING S.R.L.**, Chișinău, Moldova.

---

## What this directory is

This directory does **not** contain the Element X iOS source. The upstream
repository is ~500 MB (including Compound design system, SDK mocks, generated
assets) and we vendor it on demand. What lives here:

| Path | Purpose |
|---|---|
| `scripts/fork-bootstrap.sh` | Clone upstream at the pinned tag, apply overlay, run XcodeGen. |
| `scripts/sync-upstream.sh` | Detect new Element X releases and surface the diff. |
| `scripts/apply-branding.sh` | String replacement + asset swap against a cloned upstream. |
| `overlays/branding.yaml` | Single source of truth for rebrand mappings. |
| `overlays/strings/` | Romanian (`ro-MD`) and Russian (`ru-RU`) translation stubs. |
| `overlays/assets/AppIcon.appiconset/` | Xcode AppIcon manifest. Image PNGs are tracked in `brand/`. |
| `overlays/Compliance/` | SwiftUI views (AI Act Art 50, eEvidence footer, GDPR export/delete). |
| `overlays/Config/HomeserverDefaults.swift` | Forces `msg.md-chat.eu` as the default provider. |

See `docs/element-x-ios-fork-plan.md` (root of `md-chat/`) for the full ~5.4k-word
strategy.

---

## Sprint 1 contract — how to fork

The instructions below are **the contract**. If anyone has questions about the
fork workflow, point them at this file. Do not improvise.

### Prerequisites

1. **Apple Developer Program enrollment** under MEGA PROMOTING S.R.L. ($99/year).
   Already active on the Mega Promoting Apple ID — no new enrollment required.
2. **D-U-N-S number** for MEGA PROMOTING S.R.L. via Dun & Bradstreet.
   **Allow 1–4 weeks** for Moldova (D&B verifies trade register manually).
   Required only if the Mega Promoting D-U-N-S is not already linked.
3. macOS Sonoma 14.5+ with **Xcode 16.1+**.
4. Homebrew tooling: `brew install mint xcodegen swiftgen swiftlint swiftformat sourcery`.
5. Optionally `mise` or `asdf` pinned to the Swift toolchain shipped with Xcode 16.

### Step 1 — Clone upstream at the pinned tag

```bash
cd /Users/macbook_nou/Projects/md-chat/client-ios
./scripts/fork-bootstrap.sh
```

The bootstrap script clones `element-hq/element-x-ios` at tag **`26.05.13`** into
`upstream/` (gitignored), checks out a detached HEAD, copies overlay files on top,
then runs:

```bash
cd upstream
swift run tools setup-project
```

This installs Mint dependencies and runs XcodeGen against the patched
`project.yml`.

### Step 2 — Apply branding

`apply-branding.sh` runs the YAML-driven string replacement (see
`overlays/branding.yaml`) plus asset swap from `brand/ios/` (one level up, in
`md-chat/brand/`). Idempotent — run it as often as you like.

```bash
./scripts/apply-branding.sh
```

### Step 3 — Verify build

```bash
cd upstream
open ElementX.xcodeproj  # the rebranded project; we keep the file name initially
```

Build the `ElementX` scheme on an iPhone 16 simulator. First run downloads the
`MatrixSDKFFI.xcframework` (~120 MB) from Element's CDN — this is fine for
Sprint 1; we will rehost it on `cdn.md-chat.eu` in Sprint 3.

### Step 4 — Sync upstream

When Element ships a new calendar version (every 2–3 weeks):

```bash
./scripts/sync-upstream.sh
```

This fetches new tags from `element-hq/element-x-ios`, prints the diff against
the currently pinned tag, and emits a Sprint planning checklist. Manual review
required — no auto-merge.

---

## Branding scope — what to expect to change

The full inventory is in `docs/element-x-ios-fork-plan.md` §§2–4. Headline:

* **Bundle identifiers**: `io.element.elementx` → `eu.mdchat.app`
  (note: `branding.yaml` uses `eu.mdchat.app`; align with `eu.md-chat.messenger`
  during App Store Connect provisioning if the latter is preferred by reviewers).
* **App Group**: `group.io.element` → `group.eu.mdchat`.
* **Keychain access group**: `$(DEVELOPMENT_TEAM).io.element` → `$(DEVELOPMENT_TEAM).eu.mdchat`.
* **Display name**: `Element X` → `MD-Chat`.
* **Marketing strings**: ~120 keys reference `Element` literally; replaced via
  `branding.yaml`.
* **Default homeserver**: `matrix.org` → `msg.md-chat.eu` (see
  `overlays/Config/HomeserverDefaults.swift`).
* **Accent colour**: Compound green `#0DBD8B` → Moldova blue `#1F4FA8`
  via `CompoundColors+MDChat` namespace.

---

## Compliance shell — what is here in Sprint 0

The four SwiftUI views under `overlays/Compliance/` cover the **must-ship-from-day-1**
regulatory surfaces. They are intentionally minimal and unwired — Sprint 1
integrates them with the homeserver REST endpoints documented at
`docs/dsr-process.md`.

| File | Regulation | Status |
|---|---|---|
| `AIDisclosureBanner.swift` | EU AI Act Art 50 (in force 2 Aug 2026) | Shell, persistent flag, RO/RU/EN copy. |
| `EEvidenceFooterView.swift` | eEvidence Regulation (in force 18 Aug 2026) | Shell, EU Rep contact, portal link. |
| `GDPRExportButton.swift` | GDPR Art 20 + RM Law 195/2024 | Shell, calls `/api/v1/users/me/export`. |
| `GDPRDeleteAccountFlow.swift` | GDPR Art 17 + 30-day grace | Shell, calls `/api/v1/users/me/delete`. |

All four use only iOS 17+ APIs (`SwiftUI`, `async/await`, `Observable`-friendly).
All four are `#Preview`-able in Xcode 16.

---

## License

This project is licensed under **AGPLv3** — see `LICENSE`. It is a derivative
work of Element X iOS, which is also AGPLv3 (see `LICENSE` `NOTICE` section).
Every distributed binary must carry an "About this app" entry pointing to the
public source of this fork at:

```
https://github.com/mega-promoting/md-chat
```

If you embed this app or fork it further: comply with AGPLv3 §13 (network use
disclosure) — surface a public "Source" link from the app's About screen.
The `EEvidenceFooterView` provides such a link by default; do not remove it.

---

## Dependencies on Sprint 1

Sprint 0 (this scaffold) cannot be built in isolation. The following blocks
the first compilable IPA:

1. Clone upstream (`fork-bootstrap.sh`).
2. Replace `brand/ios/` artwork — PNG slots are referenced from
   `overlays/assets/AppIcon.appiconset/Contents.json`. Until artwork exists,
   build will warn about missing image refs but won't fail (App Icon is set
   via Composer; alternates only).
3. Implement `CompoundColors+MDChat.swift` extension under
   `upstream/ElementX/Sources/Other/Extensions/` (instructions in
   `docs/element-x-ios-fork-plan.md` §2.3).
4. Generate APNs Auth Key (`.p8`) for `eu.mdchat.app` and configure Sygnal at
   `push.md-chat.eu`.
5. Translate `Localizable-ro-MD.strings` and `Localizable-ru-RU.strings`
   stubs (Sprint 1 budget: 40h `ro`, 30h `ru`).

---

## Contact

* Engineering: `dev@md-chat.eu`
* Security: `security@md-chat.eu` (PGP key at `https://md-chat.eu/.well-known/security.txt`)
* DPO: `dpo@megapromoting.com`
* EU Representative (Art 27 GDPR): Prighter SARL, Brussels — `eu-rep@md-chat.eu`
