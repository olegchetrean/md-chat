# MD-Chat — Social card specifications

> Production specs for owned-channel banners. Companion to `og-image-spec.md`.

## 1. Mastodon profile banner

- **Dimensions**: 1500 × 500 px (Mastodon Glitch / vanilla; same as Twitter pre-X).
- **Safe area**: avatar overlays bottom-left at ~120 × 120 px starting 50 px from the left, 60 px from the bottom. Keep critical content out of that zone.
- **Background**: navy `#1A2D4E`, optional 8% lighter radial highlight top-right.
- **Headline text** (left-aligned, vertically centered): "md-chat" wordmark Inter Bold 84 px, teal `#2DD4BF`.
- **Sub-line under wordmark**: "Sovereign messenger from Moldova" Inter Medium 28 px, snow `#F8FAFC`.
- **Right side**: decorative MC monogram, 240 × 240 px, 18% opacity, teal — bleeds slightly off the right edge.
- **Filename**: `mastodon-banner.png` (2x master `mastodon-banner@2x.png` = 3000 × 1000).
- **Notes**: avoid placing text in the bottom 160 px of the canvas — avatar + Mastodon UI cover it.

## 2. Twitter / X header

- **Dimensions**: 1500 × 500 px.
- **Safe area**: profile picture overlays bottom-left at 200 × 200 px, 30 px from left, 40 px from bottom. Avoid important content in that quadrant.
- **Mobile crop**: Twitter crops to ~1500 × 500 on desktop and ~1500 × 376 on mobile. Center critical content vertically.
- **Layout**: identical concept to Mastodon banner — wordmark + sub-line. Tweak: include the URL "md-chat.eu" Inter Medium 24 px in the top-right safe zone.
- **Filename**: `twitter-header.png`.

## 3. Twitter card (link unfurl)

- See `og-image-spec.md` — Twitter consumes the same OG image when `twitter:card="summary_large_image"` is set.
- Dedicated Twitter image only if Twitter-specific copy is needed: 1200 × 628.

## 4. LinkedIn page banner

- **Dimensions**: 1584 × 396 px.
- **Aspect ratio**: 4:1 — wider and shorter than Mastodon/Twitter. Compose horizontally.
- **Layout**: wordmark left, three trust badges right ("E2EE", "Open Source", "Verified by EVO"). Center the row vertically.
- **Background**: navy `#1A2D4E`.
- **Badges**: 56 × 56 px rounded squares, teal stroke, snow fill, navy icon.
- **Filename**: `linkedin-banner.png`.

## 5. LinkedIn post share image

- 1200 × 627 px (LinkedIn's preferred share image).
- Reuse the OG image when possible. Dedicated variant if posting a campaign.

## 6. GitHub social card (Open Graph for repos)

- **Dimensions**: 1280 × 640 px (GitHub Settings → Social preview).
- **Per repo**:
  - `md-chat/server`: title "mdchat-server" + "Sovereign messenger server (Matrix/Synapse fork)".
  - `md-chat/client-ios`: title "mdchat-ios" + "iOS client for MD-Chat".
  - …pattern: `{repo}` + one-line description from `README.md`.
- **Filename**: `github-social-{repo}.png`.

## 7. App Store / Play Store assets (out of scope for v1, listed for tracking)

- iOS App Store icon: 1024 × 1024 PNG, no transparency, no rounded corners (Apple applies the radius).
- Android adaptive icon: 432 × 432 foreground + 432 × 432 background.
- Feature graphic (Play Store): 1024 × 500.
- Screenshots: 6.5" iPhone (1284 × 2778), 6.7" iPhone (1290 × 2796), Android 16:9.

## 8. Consistent design tokens across all cards

| Token             | Value                                |
|-------------------|--------------------------------------|
| Background        | `#1A2D4E` navy                       |
| Headline color    | `#F8FAFC` snow                       |
| Accent color      | `#2DD4BF` teal                       |
| Logo placement    | Top-left or center-left, never right |
| Vertical rhythm   | 16 / 24 / 32 / 48 / 64 / 96 px steps |
| Corner radius     | 0 for banners, 12 px for badges      |
| Min text contrast | 4.5:1 (WCAG AA)                      |

## 9. Production checklist

- [ ] PNG exported at 2x, downsampled to target with Lanczos.
- [ ] Run through `oxipng -o 4 --strip safe`.
- [ ] Final size <500 KB (banners) / <300 KB (cards).
- [ ] No JPEG artifacts on text.
- [ ] Preview on actual platform after upload (Mastodon scales banners aggressively).
- [ ] Version-controlled: each banner shipped with date suffix in commit message (e.g. `mastodon-banner.png 2026-05-17`).

## 10. Future: dynamic OG via `/api/og`

Once the marketing site is up (Sprint 4), retire manual export and switch to runtime card rendering via `@vercel/og` or a Cloudflare Worker + Satori:

- One template, params: `?title=...&lang=ro|ru|en&variant=launch|blog|press`.
- Output cached at the edge with 24h TTL.
- Source: `web/app/api/og/route.tsx`.

Until that's live, this manual spec is the source of truth.
