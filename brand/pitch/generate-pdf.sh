#!/usr/bin/env bash
# SPDX-License-Identifier: CC-BY-SA-4.0
# (c) 2026 Mega Promoting SRL. Licensed under CC-BY-SA 4.0.
#
# generate-pdf.sh — Build MD-Chat-pitch.pdf + MD-Chat-OnePager.pdf
#
# Strategy:
#   1. Prefer `pandoc` (with xelatex or wkhtmltopdf) for tipographic PDF.
#   2. Fall back to `weasyprint` (Python) when pandoc unavailable.
#   3. Print clear error if neither works.
#
# Both PDFs are written next to this script.
#
# Usage:
#   bash generate-pdf.sh                 # both files
#   bash generate-pdf.sh pitch           # only the deck PDF
#   bash generate-pdf.sh onepager        # only the one-pager PDF

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

PITCH_MD="MD-Chat-Moldova-Digital-Summit.md"
PITCH_PDF="MD-Chat-pitch.pdf"
ONEPAGER_MD="MD-Chat-One-Pager.md"
ONEPAGER_PDF="MD-Chat-OnePager.pdf"

TARGETS="${1:-both}"

# ----- Helpers -------------------------------------------------------------

log()   { printf "[generate-pdf] %s\n" "$*" >&2; }
fatal() { printf "[generate-pdf] ERROR: %s\n" "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

# Pick best pandoc engine available.
pandoc_engine() {
  if have xelatex; then
    echo "--pdf-engine=xelatex"
  elif have lualatex; then
    echo "--pdf-engine=lualatex"
  elif have wkhtmltopdf; then
    echo "--pdf-engine=wkhtmltopdf"
  else
    echo ""
  fi
}

# ----- Pandoc path ---------------------------------------------------------

render_with_pandoc() {
  local src="$1" dst="$2" geometry="$3"
  local engine
  engine="$(pandoc_engine)"
  if [[ -z "$engine" ]]; then
    log "pandoc has no usable PDF engine (no xelatex/lualatex/wkhtmltopdf)"
    return 1
  fi
  log "rendering with pandoc + ${engine#--pdf-engine=}: $src -> $dst"
  pandoc "$src" \
    -o "$dst" \
    $engine \
    -V geometry:"$geometry" \
    -V mainfont="Inter" \
    -V monofont="JetBrains Mono" \
    -V linkcolor=teal \
    -V urlcolor=teal \
    --highlight-style=tango \
    || return 1
  return 0
}

# ----- WeasyPrint fallback -------------------------------------------------

render_with_weasyprint() {
  local src="$1" dst="$2" page_size="$3"
  log "rendering with weasyprint fallback: $src -> $dst"
  python3 - "$src" "$dst" "$page_size" <<'PY'
import sys
import pathlib

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
page_size = sys.argv[3]  # e.g. "A4 landscape" or "A4 portrait"

try:
    import markdown
    from weasyprint import HTML, CSS
except ImportError as exc:
    sys.stderr.write(
        "weasyprint or markdown missing. Run: pip install -r requirements.txt\n"
    )
    raise SystemExit(2) from exc

md_text = src.read_text(encoding="utf-8")
html_body = markdown.markdown(
    md_text,
    extensions=["extra", "sane_lists", "tables", "toc"],
)

css = f"""
@page {{
    size: {page_size};
    margin: 18mm 16mm;
    @bottom-left {{
        content: "MD-Chat — Moldova Digital Summit 2026";
        color: #94A3B8;
        font-size: 9pt;
        font-family: Inter, sans-serif;
    }}
    @bottom-right {{
        content: counter(page) " / " counter(pages);
        color: #94A3B8;
        font-size: 9pt;
        font-family: Inter, sans-serif;
    }}
}}
body {{
    font-family: Inter, "Helvetica Neue", Arial, sans-serif;
    color: #1A2D4E;
    font-size: 11pt;
    line-height: 1.45;
}}
h1 {{ font-size: 26pt; color: #1A2D4E; border-bottom: 3px solid #2DD4BF; padding-bottom: 6pt; }}
h2 {{ font-size: 18pt; color: #1A2D4E; margin-top: 18pt; border-left: 4px solid #2DD4BF; padding-left: 10pt; }}
h3 {{ font-size: 13pt; color: #0F766E; }}
blockquote {{
    border-left: 3px solid #FBBF24;
    margin-left: 0;
    padding: 6pt 12pt;
    background: #FFFBEB;
    color: #475569;
    font-style: italic;
}}
code {{ font-family: "JetBrains Mono", monospace; font-size: 10pt; color: #0F766E; }}
table {{ border-collapse: collapse; width: 100%; margin: 12pt 0; }}
th, td {{ border: 1px solid #E2E8F0; padding: 6pt 8pt; text-align: left; }}
th {{ background: #F1F5F9; color: #1A2D4E; }}
hr {{ border: none; border-top: 1px solid #E2E8F0; margin: 18pt 0; }}
a {{ color: #0F766E; text-decoration: none; }}
strong {{ color: #1A2D4E; }}
ul, ol {{ margin-left: 18pt; }}
li {{ margin-bottom: 4pt; }}
"""

html = f"<!doctype html><html><head><meta charset='utf-8'><title>MD-Chat</title></head><body>{html_body}</body></html>"
HTML(string=html, base_url=str(src.parent)).write_pdf(
    target=str(dst),
    stylesheets=[CSS(string=css)],
)
print(f"OK  {dst}")
PY
}

# ----- Renderer dispatcher -------------------------------------------------

render() {
  local src="$1" dst="$2" geometry_pandoc="$3" page_weasy="$4"
  if [[ ! -f "$src" ]]; then
    fatal "source not found: $src"
  fi

  if have pandoc; then
    if render_with_pandoc "$src" "$dst" "$geometry_pandoc"; then
      log "pandoc OK: $dst"
      return 0
    fi
    log "pandoc failed; falling back to weasyprint"
  else
    log "pandoc not installed; using weasyprint"
  fi

  if have python3; then
    render_with_weasyprint "$src" "$dst" "$page_weasy"
    log "weasyprint OK: $dst"
    return 0
  fi

  fatal "neither pandoc nor python3+weasyprint available — cannot render $dst"
}

# ----- Run -----------------------------------------------------------------

case "$TARGETS" in
  pitch)
    render "$PITCH_MD" "$PITCH_PDF" "a4paper,landscape,margin=15mm" "A4 landscape"
    ;;
  onepager)
    render "$ONEPAGER_MD" "$ONEPAGER_PDF" "a4paper,portrait,margin=18mm" "A4 portrait"
    ;;
  both|"")
    render "$PITCH_MD" "$PITCH_PDF" "a4paper,landscape,margin=15mm" "A4 landscape"
    render "$ONEPAGER_MD" "$ONEPAGER_PDF" "a4paper,portrait,margin=18mm" "A4 portrait"
    ;;
  *)
    fatal "unknown target '$TARGETS' (use: pitch | onepager | both)"
    ;;
esac

log "done."
