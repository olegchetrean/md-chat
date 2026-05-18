<!--
SPDX-License-Identifier: CC-BY-SA-4.0
© 2026 Mega Promoting SRL — Licensed under Creative Commons Attribution-ShareAlike 4.0 International.
-->

# MD-Chat — Moldova Digital Summit pitch

Acest folder conține artefactele de pitch pentru sesiunea **MD-Chat la Moldova Digital Summit 2026** (5–6 iunie 2026). Toate fișierele sunt source-of-truth: pitch-ul „live" este generat din Markdown, nu invers.

## Cele 4 artefacte generate

| Fișier | Format | Audiență | Cum se generează |
|---|---|---|---|
| `MD-Chat-Moldova-Digital-Summit.md` | Markdown 12 slide-uri + speaker notes | Source-of-truth pentru deck | scris manual; editat aici |
| `MD-Chat-pitch.pptx` | PowerPoint 13 slide-uri (1 titlu + 12 conținut) | Proiector la summit | `python generate-pptx.py` |
| `MD-Chat-pitch.pdf` | PDF tipăribil A4 landscape | Hand-out + arhivă | `bash generate-pdf.sh` |
| `MD-Chat-OnePager.pdf` | PDF 2 pagini A4 portrait | Hand-out STISC / AGE / ministere | `bash generate-pdf.sh` |

Plus 2 fișiere de suport:

- `MD-Chat-One-Pager.md` — sursa one-pager (2 pagini condensate)
- `speaker-notes.md` — guidance per slide (100-200 cuv/slide), tranziții, Q&A canate

## Quickstart

```bash
# 1. Instalează dependențele Python (o singură dată)
python3 -m pip install -r requirements.txt

# 2. Generează PPTX
python3 generate-pptx.py --output ./MD-Chat-pitch.pptx

# 3. Generează ambele PDF-uri (pandoc preferat, fallback weasyprint)
bash generate-pdf.sh
```

## Brand styling aplicat

Configurația vizuală urmează `brand/colors.css` (dark theme):

- **Background**: navy `#1A2D4E`
- **Accent line + bullet markers**: teal `#2DD4BF`
- **Text principal**: snow `#F8FAFC`
- **Text secundar**: slate `#94A3B8` (variantă deschisă pentru contrast pe navy)
- **Font**: Inter (fallback la system sans-serif dacă nu există pe mașina prezentatoare)
- **Format slide**: 16:9 widescreen, 13.33in × 7.5in
- **Title size**: `Pt(36)` bold, **Body**: `Pt(20)` regular

Logo placeholder: slide-ul de titlu rezervă un slot 1.5in × 1.5in pentru `brand/logo-primary.svg` (nu se importă automat — paste manual în PPTX dacă e nevoie).

## Cerințe runtime

- Python **3.10+** (pentru `python-pptx` 1.0)
- `pandoc` ≥ 3.0 cu LaTeX (opțional, pentru PDF de calitate tipografică)
- `weasyprint` ≥ 63 (fallback PDF, instalat via `requirements.txt`)

## Strategie fallback PDF

`generate-pdf.sh` rulează în ordine:

1. **pandoc** cu engine `xelatex` (sau `wkhtmltopdf` dacă lipsește LaTeX) — output de calitate tipografică, ligaturi corecte, diacritice OK.
2. Dacă pandoc nu există sau dă eroare → **weasyprint** rulează direct din Python pe Markdown → HTML → PDF. Calitate suficientă pentru hand-out.
3. Dacă ambele eșuează → mesaj clar de eroare cu link la instrucțiuni de instalare.

PPTX-ul nu are fallback — `python-pptx` e singura cale viabilă fără Google Slides API.

## Licență

Conținutul markdown + scripturile: **CC-BY-SA 4.0** (Creative Commons Attribution-ShareAlike). Atribuire: „Mega Promoting SRL, MD-Chat pitch, github.com/olegchetrean/md-chat".

PDF-urile / PPTX-ul generate moștenesc licența markdown-ului sursă.
