# MD-Chat — Open Graph image specification

> Spec for the social preview image rendered when md-chat.eu links are shared.
> Companion to `brand/social-card-spec.md`. Source: brand-spec §10.3.

## File output

| Format | Size       | Purpose                       | Filename                |
|--------|------------|-------------------------------|-------------------------|
| PNG    | 1200 × 630 | Open Graph default            | `og-image.png`          |
| PNG    | 1200 × 630 | Open Graph dark variant       | `og-image-dark.png`     |
| PNG    | 1200 × 1200| Square (LinkedIn fallback)    | `og-image-square.png`   |

PNGs are the deliverable. SVG source masters live in `brand/og/`.
Aim for <300 KB per PNG (Twitter caps at 5 MB, Facebook recompresses anything bigger).

## Canvas

- Dimensions: 1200 × 630 px
- Safe area: 60 px inset on all sides (no critical content inside the outer border, in case platforms crop).
- Pixel density: 2x master (2400 × 1260) downsampled.

## Layout grid

```
+----------------------------------------------------------+
|  [60px safe inset]                                       |
|                                                          |
|   [Logo MC]   md-chat                                    |
|    96×96       Inter Bold 48 px                          |
|                                                          |
|                                                          |
|         Mesageria ta.                                    |
|         Statul tău.                                      |
|         Inteligența ta.                                  |
|         Inter Bold 88 px, leading 1.05                   |
|                                                          |
|                                                          |
|   Sovereign messenger · Made in Moldova · E2EE           |
|   Inter Medium 24 px                                     |
|                                                          |
|                                          [Teal accent]   |
|  [60px safe inset]                                       |
+----------------------------------------------------------+
```

## Colors

- Background: `#1A2D4E` (navy) — solid, no gradient.
- Optional subtle radial highlight at top-right, 5–8% lighter, 600 px radius. Keeps it from feeling flat.
- Headline text: `#F8FAFC` (snow).
- Tagline meta text: `#2DD4BF` (teal).
- Logo monogram: teal on navy circle.

## Typography

- Headline: Inter Bold, 88 px, leading 1.05, letter-spacing -0.02em.
- Meta line: Inter Medium, 24 px, letter-spacing 0.01em, ALL lowercase except proper nouns.
- Wordmark beside logo: Inter Bold 48 px, lowercase.

## Variants by locale

Same layout, different headline:

- **RO** (default): "Mesageria ta. Statul tău. Inteligența ta."
- **RU**: "Твой мессенджер. Твоё государство. Твой ИИ."
- **EN**: "Sovereign by design. Smart by choice."

Filename pattern: `og-image-{lang}.png`.

## Variants by context

- `og-image-launch.png` — adds small "LAUNCH 2026" gold pill, bottom-right.
- `og-image-blog.png` — generic, no campaign overlay.
- `og-image-press.png` — adds "PRESS KIT" label, links to /press.

## Accessibility

Even though OG images are decorative, set the `alt` attribute on the `<meta property="og:image:alt">` tag:

```
<meta property="og:image" content="https://md-chat.eu/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="MD-Chat — sovereign messenger from Moldova. Tagline: Mesageria ta. Statul tau. Inteligenta ta.">
<meta property="og:image:type" content="image/png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://md-chat.eu/og-image.png">
<meta name="twitter:image:alt" content="MD-Chat sovereign messenger preview">
```

## How to produce the PNG

Until automated rendering is in place, produce via one of:

1. **Figma**: open `brand/og/og-master.fig`, export 2x PNG. Frame name `og-1200x630`.
2. **Headless Chrome**: render `brand/og/og-template.html` at viewport 1200×630, screenshot.
3. **Resvg / Inkscape**: render `brand/og/og-master.svg` at 1200×630.

When the marketing site lands (Sprint 4), replace this manual process with an `/api/og` route that renders per-page OG cards from a single template.

## QA checklist

- [ ] Logo crisp at 96 px (no SVG export rounding artifacts).
- [ ] Diacritics in RO headline render correctly (ț, ă).
- [ ] Cyrillic in RU headline renders correctly (Ё distinct from Е).
- [ ] File size <300 KB after pngquant / oxipng pass.
- [ ] Preview tested in:
  - [ ] Facebook Sharing Debugger
  - [ ] Twitter Card Validator (or Card Validator Lite)
  - [ ] LinkedIn Post Inspector
  - [ ] Slack unfurl
  - [ ] Telegram link preview (yes, still relevant)
  - [ ] Discord unfurl
