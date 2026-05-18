# Flavors — gplay vs fdroid

The Android build defines two product flavors using the `store` dimension
inherited from upstream Element X Android.

## `gplay`

- Distribution: Google Play Store (closed → open testing → production).
- Push: Firebase Cloud Messaging (FCM). Sender ID configured via env at build.
- Crash reporting: Sentry self-hosted (no Crashlytics).
- Analytics: PostHog self-hosted (no Google Analytics, no Firebase Analytics).
- Telemetry: opt-in only.
- Signing: separate keystore from fdroid flavor.

## `fdroid`

- Distribution: self-hosted repo at `fdroid.md-chat.eu` (immediate) + mainline
  F-Droid auto-fetch (when accepted).
- Push: UnifiedPush. Falls back to long-poll if no distributor is installed.
  See `overlays/UnifiedPush/UnifiedPushConfig.kt`.
- Reproducible build: yes. Gradle settings inherited from upstream Element X
  Android (`reproducibleBuild = true`).
- No Google Play Services library at all (verified at build time).
- Signing: separate keystore from gplay flavor.

## When to use which

- Default Android users → recommend `gplay` for battery/reliability.
- Power users + privacy-conscious + non-Google devices → recommend `fdroid`.
- Documented in README + on the website download page.

## Build commands

```bash
./gradlew assembleGplayDebug
./gradlew assembleFdroidDebug
./gradlew bundleGplayRelease
./gradlew assembleFdroidRelease
```

## Configuration env vars

| Variable | gplay | fdroid |
|---------|-------|--------|
| `FCM_SENDER_ID` | required | unused |
| `FCM_API_KEY` | required | unused |
| `UNIFIEDPUSH_DEFAULT_DISTRIBUTOR` | unused | optional |
| `SENTRY_DSN` | optional | optional |
| `POSTHOG_API_KEY` | optional | optional |
