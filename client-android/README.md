# MD-Chat Android — Element X Fork Shell

> **Status:** Scaffolding overlay (no upstream sources vendored)
> **Upstream:** [`element-hq/element-x-android@v26.05.1`](https://github.com/element-hq/element-x-android/releases/tag/v26.05.1)
> **Downstream:** `olegchetrean/md-chat-android` (to be created)
> **License:** AGPL-3.0-or-later (upstream is dual AGPL/commercial; we publish source so we ride the AGPL track only)
> **Operator:** MEGA PROMOTING S.R.L., Chișinău, Republic of Moldova
> **Companion plan:** [`/docs/element-x-android-fork-plan.md`](../docs/element-x-android-fork-plan.md)

This directory is **not** a checked-in copy of Element X Android. It is the
*overlay* — branding, compliance modules, build-flavor wiring, and helper
scripts that get applied **on top of** a freshly cloned upstream tree. The
goal is that anyone with a clean machine and ~2 hours can produce signed
`gplay` and `fdroid` builds of MD-Chat Android.

---

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| JDK | 21 (Temurin) | Element X uses JVM target 21 via the Gradle toolchain |
| Android SDK | platform 36, build-tools 35.0.1+ | install via `sdkmanager` |
| Android Studio | Hedgehog 2026.05 or newer | optional — `./gradlew` works headless |
| Kotlin | 2.3.21 (managed by Gradle wrapper) | do not install globally |
| Git | 2.40+ | |
| `yq` | 4.x | YAML processing in `apply-branding.sh` |
| `cwebp` | 1.3+ | mipmap re-compression |
| Play Console account | $25 one-time | required only for `gplay` release uploads |
| Fastlane (optional) | 2.225+ | used by the release workflow |

---

## 2. Bootstrap a working fork

```bash
cd /path/where/you/keep/sources
git clone https://github.com/element-hq/element-x-android.git md-chat-android
cd md-chat-android
git checkout v26.05.1
git remote add upstream https://github.com/element-hq/element-x-android.git
git remote set-url origin git@github.com:olegchetrean/md-chat-android.git

# Apply the overlay
bash /path/to/this/repo/client-android/scripts/fork-bootstrap.sh \
    --overlay /path/to/this/repo/client-android/overlays \
    --branch  mdchat-init
```

The bootstrap script:

1. Verifies you are on tag `v26.05.1` (or whatever `--ref` you passed).
2. Copies the four `Compliance/*.kt` files into
   `features/preferences/impl/src/main/kotlin/eu/mdchat/compliance/`.
3. Copies `UnifiedPushConfig.kt` into
   `libraries/pushproviders/unifiedpush/src/main/kotlin/eu/mdchat/push/`.
4. Copies `HomeserverDefaults.kt` into
   `appconfig/src/main/kotlin/eu/mdchat/appconfig/` and re-routes
   `AuthenticationConfig` to it.
5. Merges the per-locale `strings.xml` files into
   `libraries/ui-strings/src/main/res/values*/`.
6. Runs `apply-branding.sh` which performs the YAML-driven literal
   replacements (Element → MD-Chat, application ID, default homeserver).
7. Drops the `:features:enterprise` module from `settings.gradle.kts`
   and from the dependency graph.
8. Generates a commit `mdchat: initial fork` with the changes.

---

## 3. Build

Both flavors must build clean before you push.

```bash
./gradlew :app:assembleGplayDebug :app:assembleFdroidDebug
./gradlew :app:bundleGplayRelease            # AAB for Play Console
./gradlew :app:assembleFdroidRelease         # APK for F-Droid
./gradlew detekt ktlintCheck konsistTest     # full static analysis
./gradlew testGplayDebugUnitTest             # unit tests
```

The two flavors coexist on a single device:

- `gplay` → `eu.mdchat.android`
- `fdroid` → `eu.mdchat.android.fdroid`

See [`flavors.md`](./flavors.md) for the full contract.

---

## 4. Weekly upstream rebase

We track upstream `develop` and tagged releases at a deliberate lag — they
ship monthly, we ship every 6 weeks so we have a 2-week soak window.

```bash
# Mondays — automated via .github/workflows/upstream-merge.yml
bash client-android/scripts/sync-upstream.sh --check
bash client-android/scripts/sync-upstream.sh --merge --branch mdchat-upstream-$(date +%Y%m%d)
```

The merge driver re-runs `apply-branding.sh` after each merge so the
literal replacements are mechanical, not manual.

**Hotspot files** (expect conflicts every release):

- `appconfig/AuthenticationConfig.kt`
- `app/build.gradle.kts`
- `libraries/designsystem/.../theme/*`
- `app/src/main/AndroidManifest.xml`
- `libraries/ui-strings/src/main/res/values*/strings.xml`

The repo's `.gitattributes` marks `overlays/branding.yaml` as
`merge=ours` so the canonical substitution list is never auto-clobbered.

---

## 5. Play Store (gplay flavor)

1. Open a **Google Play Console** developer account at
   <https://play.google.com/console/signup> — $25 one-time fee, ~1
   business day to verify Moldova-issued identity. Register under
   "MEGA PROMOTING S.R.L." (organization account).
2. Create an internal app `eu.mdchat.android`. Privacy policy URL is
   mandatory: `https://md-chat.eu/legal/privacy`.
3. Fill the **Data safety form** truthfully — see
   `docs/element-x-android-fork-plan.md` §5.
4. Set **target audience** to 18+ for v1.0 (sidesteps COPPA / under-13
   parental consent flows on the first ship).
5. Submit the first build to the **Closed testing** track with 20+
   testers for **14 days minimum** (Play policy). Promote to
   production only after that window closes with no critical bugs.
6. CI workflow `.github/workflows/android-release.yml` uses
   [`r0adkll/upload-google-play`](https://github.com/r0adkll/upload-google-play)
   with the `PLAY_SERVICE_ACCOUNT_JSON` secret (release-manager-only
   GitHub Environment).

---

## 6. F-Droid (fdroid flavor)

F-Droid bans proprietary blobs, which means **no FCM**. The `fdroid`
flavor wires [UnifiedPush](https://unifiedpush.org/) instead — the user
picks a distributor app (NextPush, ntfy, etc.) at first launch.

### Metadata YAML

Submit to <https://gitlab.com/fdroid/fdroiddata> as
`metadata/eu.mdchat.android.yml`:

```yaml
Categories:
  - Internet
License: AGPL-3.0-or-later
AuthorName: MEGA PROMOTING S.R.L.
AuthorEmail: contact@md-chat.eu
WebSite: https://md-chat.eu
SourceCode: https://github.com/olegchetrean/md-chat-android
IssueTracker: https://github.com/olegchetrean/md-chat-android/issues
Changelog: https://github.com/olegchetrean/md-chat-android/blob/main/CHANGELOG.md

RepoType: git
Repo: https://github.com/olegchetrean/md-chat-android

Builds:
  - versionName: 26.05.1-mdchat.1
    versionCode: 26260101
    commit: vYY.MM.N-mdchat.M
    subdir: app
    gradle:
      - fdroid
    ndk: r26d

AutoUpdateMode: Version
UpdateCheckMode: Tags
UpdateCheckData: app/build.gradle.kts|versionName\s*=\s*"(.+?)"|.|versionCode\s*=\s*(\d+)
CurrentVersion: 26.05.1-mdchat.1
CurrentVersionCode: 26260101
```

### Reproducible builds

F-Droid requires byte-for-byte reproducibility. We pin:

- `cimg/android:2026.05` Docker image by SHA digest in CI.
- `gradle/verification-metadata.xml` (`./gradlew --write-verification-metadata sha256`).
- `SOURCE_DATE_EPOCH` derived from the git tag commit timestamp.

### Self-hosted F-Droid repo

While mainline F-Droid review is 2-6 weeks, we publish same-day updates
to `https://fdroid.md-chat.eu/repo` (managed by `fdroidserver` on the
release runner). Users add it via QR code.

### Anti-Features

We expect `NonFreeNet` (Matrix federation can reach proprietary
homeservers) and possibly `Tracking` (PostHog opt-in is debated). Both
are pre-negotiated in the upstream metadata PR description.

---

## 7. Compliance surfaces

All four compliance Kotlin modules sit in `overlays/Compliance/` and are
applied via `fork-bootstrap.sh`:

| File | Hooks into | Purpose |
|---|---|---|
| `AIDisclosureBanner.kt` | `:features:messages` composer | AI Act Art. 50 modal + persistent banner on AI-flagged rooms |
| `EEvidenceFooter.kt` | `:features:preferences` → About | EU eEvidence Reg. 2023/1543 footer with EU Representative + production-order portal link |
| `GDPRExportButton.kt` | `:features:preferences` → Privacy | GDPR Art. 15 + 20 export — invokes Synapse `/account/export` |
| `GDPRDeleteAccountFlow.kt` | `:features:preferences` → Privacy | GDPR Art. 17 right to erasure with 30-day grace period |

Sprint 1 dependency: the server side (`/server/`) must expose
`POST /account/export` and the `delete_scheduled_at` cron from
`docs/element-x-android-fork-plan.md` §11 before the Android Delete
button is shipped publicly.

---

## 8. Project layout

```
client-android/
├── README.md                       (this file)
├── LICENSE                         AGPL-3.0
├── CHANGELOG.md                    Keep-a-Changelog skeleton
├── flavors.md                      gplay vs fdroid contract
├── proguard-rules-mdchat.pro       R8 keep rules overlay
├── .gitignore                      Android Studio / Gradle / build outputs
├── scripts/
│   ├── fork-bootstrap.sh           one-shot: clone upstream + overlay
│   ├── sync-upstream.sh            weekly Monday merge driver
│   └── apply-branding.sh           literal substitutions from branding.yaml
└── overlays/
    ├── branding.yaml               canonical string/identifier table
    ├── res/
    │   ├── values/strings.xml          en (baseline)
    │   ├── values-ro-rMD/strings.xml   ro-MD
    │   ├── values-ru/strings.xml       ru
    │   └── values-uk/strings.xml       uk
    ├── Compliance/
    │   ├── AIDisclosureBanner.kt
    │   ├── EEvidenceFooter.kt
    │   ├── GDPRExportButton.kt
    │   └── GDPRDeleteAccountFlow.kt
    ├── UnifiedPush/
    │   └── UnifiedPushConfig.kt
    └── Config/
        └── HomeserverDefaults.kt
```

---

## 9. License

The upstream Element X Android codebase is AGPL-3.0-or-later (with a
commercial dual-license offered by Element). Because we publish our
fork's source code openly, we stay strictly on the AGPL-3.0 track. The
overlay files in *this directory* are also AGPL-3.0 — see
[`LICENSE`](./LICENSE).

Brand assets (the "MD-Chat" name, logos in `/brand/`) are **not** part
of the AGPL grant. Forks must remove brand assets — see the F-Droid
trademark policy and `docs/brand-policy.md`.
