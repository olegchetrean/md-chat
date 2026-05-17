# MD-Chat — Brand assets

This directory contains the production brand assets for MD-Chat, the sovereign messenger built in Moldova to EU standards. The canonical brand specification lives at:

`Reports/2026-05-17-EU-Messengers/Drafts/03-Brand-Spec-MDChat.md`

This README is the **operational** guide — what's in this folder, how to use each file, what's still to come.

---

## 1. What's here

| File                          | Purpose                                                      |
|-------------------------------|--------------------------------------------------------------|
| `README.md`                   | This file. Brand guide overview.                             |
| `logo-primary.svg`            | Full-color primary logo — teal MC on navy circle, 512 viewBox |
| `logo-monochrome-light.svg`   | Single color on dark backgrounds (snow on navy)              |
| `logo-monochrome-dark.svg`    | Single color on light backgrounds (navy on snow)             |
| `logo-wordmark.svg`           | Wordmark only — `md-chat` lowercase, teal on navy            |
| `app-icon.svg`                | 1024×1024 square with Apple HIG 22.37% corner radius         |
| `favicon.svg`                 | Minimal 32×32 viewBox favicon                                |
| `colors.css`                  | CSS custom properties for all brand + status colors          |
| `typography.css`              | `@font-face` + type scale utilities                          |
| `voice-tone.md`               | Voice & tone guide (extracted from spec §5)                  |
| `og-image-spec.md`            | Open Graph image production spec                             |
| `social-card-spec.md`         | Mastodon / Twitter / LinkedIn / GitHub card specs            |
| `press-release-RO.md`         | Romanian launch press release                                |
| `press-release-EN.md`         | English launch press release                                 |
| `press-release-RU.md`         | Russian launch press release (Cyrillic native)               |

---

## 2. Brand at a glance

**Name**: MD-Chat (consumer-facing). `md-chat` lowercase for URLs and files. `mdchat` alphanumeric for handles and sender IDs.

**Promise**: the smartest sovereign messenger in the EU, built for Moldova, scalable across Europe.

**Personality**: technically competent, accessible, slightly bold (never corporate boring), natively bilingual RO + RU, pro-encryption without paranoia.

**Tagline shortlist** (final pick pending):
1. "Sovereign by design. Smart by choice." (EN)
2. "Mesageria ta. Statul tău. Inteligența ta." (RO)
3. "Moldova's chat, Europe's standard."

---

## 3. Color palette

### Primary

| Token             | Hex        | Use                                          |
|-------------------|------------|----------------------------------------------|
| `--mdchat-navy`   | `#1A2D4E`  | Dark-mode bg, light-mode primary text        |
| `--mdchat-teal`   | `#2DD4BF`  | Accent, CTAs, active states                  |
| `--mdchat-snow`   | `#F8FAFC`  | Light-mode bg, neutral surface               |

### Secondary

| Token             | Hex        | Use                                |
|-------------------|------------|------------------------------------|
| `--mdchat-slate`  | `#475569`  | Secondary text, borders            |
| `--mdchat-coral`  | `#FB7185`  | Warnings, destructive actions      |
| `--mdchat-gold`   | `#FBBF24`  | Premium tier, eIDAS verified badge |

### Trust + status

| Token                | Hex        | Use                          |
|----------------------|------------|------------------------------|
| `--mdchat-verified`  | `#1E40AF`  | "Verified by EVO" badge      |
| `--mdchat-success`   | `#10B981`  | Sent, online                 |
| `--mdchat-warning`   | `#F59E0B`  | Pending, awaiting            |
| `--mdchat-error`     | `#EF4444`  | Failed, error                |
| `--mdchat-info`      | `#3B82F6`  | Notifications                |

All defined as CSS custom properties in `colors.css`, with `:root` defaults and `[data-theme="dark"]` / `[data-theme="black"]` (true black OLED) overrides.

---

## 4. Typography

- **Sans**: Inter (open source, Google Fonts). Cyrillic + Latin Extended cover RO + RU + EN + UA.
- **Mono**: JetBrains Mono. For code, technical IDs, MFA codes.
- **Fallbacks**: system fonts via `@font-face` `local()`.

Type scale mobile-first (px / line-height):

| Level   | Mobile      | Desktop     | Weight     |
|---------|-------------|-------------|------------|
| H1      | 28 / 1.2    | 36 / 1.2    | Bold       |
| H2      | 22 / 1.3    | 28 / 1.3    | Semibold   |
| H3      | 18 / 1.4    | 22 / 1.4    | Semibold   |
| Body    | 16 / 1.5    | 16 / 1.6    | Regular    |
| Small   | 14 / 1.4    | 14 / 1.5    | Regular    |
| Caption | 12 / 1.3    | 12 / 1.4    | Medium     |

Implementation: `typography.css`.

---

## 5. Logo usage

### Do

- Use `logo-primary.svg` on neutral backgrounds.
- Use `logo-monochrome-light.svg` on dark photo backgrounds.
- Use `logo-monochrome-dark.svg` on light photo backgrounds.
- Keep a safe zone equal to 25% of the circle's diameter on all sides.
- Use `logo-wordmark.svg` standalone when the monogram is too small to read (below 24 px).

### Don't

- Don't recolor outside the brand palette.
- Don't rotate, skew, or stretch.
- Don't apply drop shadows, 3D extrusions, or glows.
- Don't put the logo inside a colored container (it always free-stands).
- Don't pair MD-Chat lockup with the Mega Promoting logo in the same artwork — MD-Chat is a standalone brand.
- Don't recreate the monogram in a different font; always use the SVG.

### Minimum sizes

- Primary logo: 24 px minimum.
- Favicon: 16 px minimum (use `favicon.svg`, not a downscaled primary).
- App icon: never smaller than 40 px on iOS, 48 dp on Android.

---

## 6. Voice & tone

See `voice-tone.md` for the full guide. One-liner: confident, concrete, bilingual native, transparently technical when it matters.

Forbidden phrases (excerpt): "revolutionary", "disrupt", "bank-grade encryption", "military-grade encryption", "unhackable", "AI-powered" (in consumer copy — describe what the AI does instead).

---

## 7. Press kit

Launch press releases shipped in three languages:

- `press-release-RO.md` — Romanian
- `press-release-EN.md` — English
- `press-release-RU.md` — Russian (Cyrillic native, not transliteration)

Contact: `contact@md-chat.eu`.

A full press kit ZIP — including logo PNGs at 16/32/64/128/256/512/1024/2048, founder photo, and product screenshots — will ship at `press/press-kit.zip` once the marketing site is live (Sprint 4).

---

## 8. Open Graph + social

- `og-image-spec.md` — Open Graph image production spec for `og-image.png`.
- `social-card-spec.md` — Mastodon banner (1500×500), Twitter header (1500×500), LinkedIn banner (1584×396), GitHub social cards (1280×640).

Until automated `/api/og` rendering lands, OG cards are produced manually from the Figma master in `brand/og/`.

---

## 9. License

- Brand assets: **CC-BY-SA 4.0**. You may copy, modify, redistribute with attribution back to MD-Chat.
- Logo and wordmark: **trademarks** of Mega Promoting SRL. Use is **not** permitted for commercial competitors. Free for press, education, and fan content.

---

## 10. Versioning

This brand guide is **v1**, generated 2026-05-17.

Changes to the palette, logo, or voice & tone require:

1. An RFC in `docs/rfcs/` proposing the change.
2. Approval from Oleg Chetrean (founder) + design lead.
3. A new version tag (`brand-v2`) and migration notes for downstream apps.

For typo fixes and clarifications, PR directly against this directory.

---

## 11. Quick reference

```html
<!-- HTML head -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="/brand/typography.css">
<link rel="stylesheet" href="/brand/colors.css">
<link rel="icon" type="image/svg+xml" href="/brand/favicon.svg">

<!-- OG -->
<meta property="og:image" content="https://md-chat.eu/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
```

```css
/* In your app */
.cta {
  background: var(--mdchat-teal);
  color: var(--mdchat-navy);
  font-family: var(--font-sans);
  font-weight: 500;
}
```

That's it. Welcome to MD-Chat.
