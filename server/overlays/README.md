<!--
SPDX-License-Identifier: AGPL-3.0-only
SPDX-FileCopyrightText: 2026 Mega Promoting SRL
-->

# Overlay format

This directory is the **source of truth** for everything that makes upstream
Synapse into MD-Chat Server. Three overlay types coexist; they are applied in
this order by `../scripts/apply-overlays.sh`:

1. `strings/*.yaml` — declarative string-replace
2. `templates/*.j2|*.html|*.txt` — Jinja2/HTML/TXT files that shadow upstream
3. `patches/*.patch` — unified-diff patches applied with `patch -p1`

When in doubt, prefer the *least invasive* overlay: a string-replace beats a
template overlay, a template overlay beats a code patch.

---

## 1. String overlays — `strings/*.yaml`

Use when a brand token appears identically in many files (e.g., `Element` →
`MD-Chat`, `support@element.io` → `support@md-chat.eu`).

### Schema

```yaml
# strings/example.yaml
version: 1
description: "Short human-readable summary of what this overlay does."

entries:
  - path: "synapse/res/templates/*.html"   # glob, relative to Synapse source root
    replace:
      - ["Element", "MD-Chat"]              # [from, to]
      - ["element.io/help", "md-chat.eu/help"]
    dry_run: false                          # optional, default false

  - path: "synapse/handlers/identity.py"
    replace:
      - ["[%s] Password reset", "[%s] Resetare parolă MD-Chat"]
```

### Rules

- `path` is a glob, evaluated relative to the **Synapse source root** (i.e.,
  the directory that contains `synapse/`, `tests/`, `pyproject.toml`).
- `replace` is a list of `[from, to]` pairs. Plain string match (no regex).
  Replacement is exact and case-sensitive.
- `dry_run: true` — the overlay is logged but no file is modified. Useful for
  staging large brand changes.
- If a glob matches **zero files**, the overlay aborts with exit code 10 —
  upstream has drifted and the glob needs updating.
- An entry can match zero *occurrences* across all files without aborting —
  this is common after upstream removes a phrase. Track this in CHANGELOG.

### Why not regex

Regex causes pain at upstream rebase time because anchors and character
classes silently break. Plain-string replace forces us to update the YAML
when upstream changes a phrase — which is exactly when we want a CI failure
to wake us up.

---

## 2. Template overlays — `templates/*.j2`, `*.html`, `*.txt`

Use when a Jinja2 template needs a structural change that string-replace
cannot express (logo swap, conditional block removal, footer rewrite).

### Mechanism

Files are copied verbatim to `synapse/res/templates/<basename-without-j2>`,
overwriting the upstream template. Synapse reads from this directory at
startup, so the overlay is effective at runtime.

In production we also expose the same templates via
`templates.custom_template_directory: /data/templates/mdchat/` in
`homeserver.yaml` — that path is the volume-mounted copy, allowing runtime
edits without rebuilding the image.

### Naming convention

- `welcome.html.j2` → `synapse/res/templates/welcome.html`
- `notif_mail.html.j2` → `synapse/res/templates/notif_mail.html`

The `.j2` suffix is a marker for editor syntax-highlighting on disk; it is
stripped on apply.

### Rules

- Always start from a copy of the upstream template at the pinned tag.
- Keep all `{% block %}` / `{% endblock %}` tags identical to upstream — this
  preserves the inheritance graph and avoids subtle render errors.
- Never embed brand strings that are also handled by a `strings/*.yaml`
  overlay — choose one mechanism per string.

---

## 3. Code patches — `patches/*.patch`

Use **only** when the change is structural (new HTTP route, new module
import) and cannot be expressed as a string-replace or template overlay.

### Format

- Unified diff, generated with `git format-patch -1 -o overlays/patches/`.
- Filename: `NNNN-short-slug.patch`, where `NNNN` is a 4-digit ordinal.
  Patches are applied in lexical order.
- Patch is applied with `patch -p1` from the Synapse source root. Make sure
  your diff paths start with `a/synapse/...` and `b/synapse/...`.
- Each patch is independently reversible. Avoid coupling unrelated changes
  inside a single patch.

### Authoring workflow

```bash
# inside a fresh upstream checkout:
git checkout -b mdchat/feature-name v1.121.0
# ...edit files...
git commit -am "feature: short slug"
git format-patch -1 -o /path/to/server/overlays/patches/
# rename to follow NNNN-... convention
```

### Idempotency

`apply-overlays.sh` first does `patch --dry-run`; if that fails, it tries
`patch --dry-run -R`. If reverse-apply succeeds, the patch is already
applied and is skipped. This makes re-running safe.

If neither direction applies cleanly, upstream has drifted. Action:
1. Resync upstream tag in `Dockerfile` (`SYNAPSE_VERSION`).
2. Re-rebase the patch by hand against the new tag.
3. `git format-patch` again, overwrite the file.

---

## 4. Order of application & precedence

```
strings/*.yaml   (alphabetical)
└─ templates/    (alphabetical)
   └─ patches/   (lexical, 0001 first)
```

Within a single file:
- A string-replace pair applies; then the file may be overwritten by a
  template overlay; then a patch may further modify it.
- In practice, **avoid** layering — a given file should be touched by at
  most one overlay type. If you need to combine, comment it loudly in the
  YAML / patch header.

---

## 5. License headers

Every overlay file MUST carry a license header in its native comment style:

| Overlay type | Header style |
|---|---|
| `*.yaml`     | `# SPDX-License-Identifier: AGPL-3.0-only` |
| `*.html.j2`  | `{# SPDX-License-Identifier: AGPL-3.0-only #}` |
| `*.txt.j2`   | `# SPDX-License-Identifier: AGPL-3.0-only` |
| `*.patch`    | header lines preserved from `git format-patch` (which carries SPDX from the source file) |
| `*.sh`       | `# SPDX-License-Identifier: AGPL-3.0-only` |

The build refuses to ship an unlicensed overlay.

---

## 6. Adding a new overlay — checklist

1. Identify the smallest expressive overlay type (string > template > patch).
2. Create the file with a license header.
3. Run `../scripts/apply-overlays.sh ./tmp-synapse ../overlays` against a
   throwaway upstream clone.
4. Run `../scripts/verify-overlays.sh ./tmp-synapse ../overlays`.
5. Add an entry to `../CHANGELOG.md` under `## [Unreleased]`.
6. Commit with a message starting with `overlay:` or `patch:`.
