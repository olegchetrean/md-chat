<!--
SPDX-License-Identifier: AGPL-3.0-only
SPDX-FileCopyrightText: 2026 Mega Promoting SRL
-->

# MD-Chat Server — Synapse Overlay Fork

> **What this is:** the *thin overlay* that we apply on top of an unmodified
> `element-hq/synapse` checkout to produce the **MD-Chat Server** Docker image.
>
> **What this is NOT:** a hard fork. We do not vendor the upstream Synapse
> source tree into this monorepo. The Synapse source code lives where Element
> publishes it. Our overlay is the *difference* between vanilla Synapse and
> MD-Chat Server.

---

## 1. Strategy: overlay-on-rebase, not hard fork

We picked the **overlay-on-rebase** strategy after evaluating three options
(see `docs/synapse-rebrand-plan.md`, §11.2):

| Strategy | Pros | Cons | Verdict |
|---|---|---|---|
| **Hard fork** (vendor Synapse into our repo) | full control | merge hell on every upstream tag, AGPL §13 source-disclosure burden ×10, `git blame` lies | rejected |
| **Squash overlay** (one big "MD-Chat changes" commit on top of upstream) | clean diff | destroys per-file SPDX attribution, security-patch cherry-picks become guesswork | rejected |
| **Rebase overlay** (this repo) — patches + string-replace tables applied at build time onto a pinned upstream tag | tiny diff (~6 Python lines + ~28 string overlays), trivial rebase on each upstream tag, per-file SPDX preserved, AGPL §13 source-disclosure is a one-line link to upstream + this repo | requires a build script (provided) | **chosen** |

The patch set is intentionally tiny. If we find ourselves adding more than ~50
lines of Python diff, we have crossed into "hard fork" territory and should
reconsider — either upstream the change to Synapse or implement it as an
external **Synapse module** (see §6).

---

## 2. Directory layout

```
server/
├── README.md                        ← this file
├── CHANGELOG.md                     ← MD-Chat-side changes only
├── LICENSE                          ← AGPLv3 boilerplate + downstream NOTICE
├── Dockerfile                       ← multi-stage: clone Synapse → apply overlays → ship
├── .dockerignore
├── scripts/
│   ├── sync-upstream.sh             ← check for new Synapse releases (run weekly)
│   ├── apply-overlays.sh            ← idempotent overlay application
│   └── verify-overlays.sh           ← sanity check post-apply
└── overlays/
    ├── README.md                    ← overlay format spec
    ├── strings/
    │   ├── branding.yaml            ← simple string-replace table (path-glob → [from, to])
    │   └── email-subjects.yaml      ← Python-source patches expressed as before/after pairs
    ├── templates/                   ← Jinja2 templates that shadow synapse/res/templates/
    │   ├── welcome.html.j2
    │   └── password-reset.html.j2
    └── patches/                     ← unified-diff patches applied with `patch -p1`
        └── 0001-add-source-disclosure-endpoint.patch
```

`overlays/` is the *source of truth* for everything that makes vanilla Synapse
into MD-Chat Server. The Dockerfile is just glue.

---

## 3. How to build locally

```bash
# from this directory
docker build -t mdchat-synapse:dev .
docker run --rm -e SYNAPSE_SERVER_NAME=msg.md-chat.eu \
           -e SYNAPSE_REPORT_STATS=no \
           mdchat-synapse:dev generate
docker run --rm -p 8008:8008 -v "$(pwd)/data:/data" mdchat-synapse:dev
```

The build:
1. starts from `python:3.12-slim`,
2. clones `element-hq/synapse` at the pinned tag (`SYNAPSE_VERSION` build-arg,
   default **v1.121.0** — the tag verified in `docs/synapse-rebrand-plan.md`),
3. runs `scripts/apply-overlays.sh` against the cloned tree,
4. runs `scripts/verify-overlays.sh` to confirm every overlay applied,
5. installs Synapse + extras via `pip`,
6. emits an OCI image labelled with `org.opencontainers.image.source` pointing
   at the public MD-Chat fork (AGPL §13).

The build is **deterministic** for a given upstream tag — the same overlay set
plus the same `SYNAPSE_VERSION` always produces the same Synapse source tree.

---

## 4. How to bump upstream

```bash
./scripts/sync-upstream.sh                # prints latest upstream tag vs ours
# if drift detected:
git checkout -b chore/bump-synapse-v1.122.0
# edit Dockerfile: ARG SYNAPSE_VERSION=v1.122.0
docker build -t mdchat-synapse:test .     # apply-overlays.sh fails fast on drift
./scripts/verify-overlays.sh ./build-tmp  # or rely on the in-Docker verify step
git commit -am "chore: bump Synapse to v1.122.0"
```

If any overlay fails to apply (`patch` returns non-zero or a string-replace
finds zero occurrences), the build aborts and a CI issue is opened. Fix-up
strategy is in `docs/synapse-rebrand-plan.md` §11.

CI runs `sync-upstream.sh` on a weekly cron. On security advisories
(GHSA on `element-hq/synapse`), the cron triggers a 24h hot-fix workflow.

---

## 5. Overlay grammar

There are three overlay types, evaluated in this order by
`apply-overlays.sh`:

1. **`overlays/strings/*.yaml`** — declarative string replacements scoped by
   path-glob. Use this for brand strings, support emails, default values that
   are repeated in many files. Each YAML entry has `path` (glob), `replace`
   (list of `[from, to]` pairs), and an optional `dry_run` flag.
2. **`overlays/templates/*.html.j2`** — Jinja2 templates that shadow the
   upstream ones at `synapse/res/templates/`. Synapse already supports loading
   custom templates via `email.template_dir` in `homeserver.yaml`; we mount
   ours at `/data/templates/mdchat/`.
3. **`overlays/patches/*.patch`** — unified-diff files applied with
   `patch -p1`. Use this *only* when string-replace cannot express the change
   (e.g., adding a new HTTP route). Patches are numbered and applied in order.

See `overlays/README.md` for the full grammar.

---

## 6. When NOT to use an overlay

If you need to add MD-Chat-specific behaviour (audit log, MPass connector,
Kallina voice bridge), write a **Synapse module** and load it via the
`modules:` section in `homeserver.yaml`. Modules live in a separate Python
package (`md-chat-extensions`) and ship their own migrations. This keeps the
overlay paper-thin and the upstream rebase trivial.

The overlay is for **rebranding only**. Everything else is a module.

---

## 7. AGPL §13 source disclosure

Because users interact with MD-Chat over a network, AGPL §13 requires us to
offer them the corresponding source. We satisfy this in three layers:

1. **Patch `0001-add-source-disclosure-endpoint.patch`** adds a `/source`
   HTTP route to Synapse that 302-redirects to the public fork repo. This is
   the only patch that *adds* functionality; everything else is a string edit.
2. **nginx** also serves `https://md-chat.eu/source` as a static redirect for
   users who do not reach Synapse directly.
3. **`LICENSE`** in this directory and `NOTICE` shipped inside the image both
   carry the link plainly.

The downstream repo URL is `https://github.com/megapromoting/md-chat-server`
(public, AGPLv3). Update the URL in `Dockerfile` and the patch if it changes.

---

## 8. Estimated effort to complete the real fork

Per `docs/synapse-rebrand-plan.md`:
- First-pass rebrand: **36–48 engineering hours** (Sprint 1).
- Quarterly upkeep: **~6 hours** per Synapse minor version.

This scaffolding burns ~2h of that budget. The remaining ~36h is split:
~10h template content + i18n, ~6h email subjects + Python patches, ~6h CI,
~6h SSO/MPass branding, ~4h verification + staging soak, ~4h documentation
sync.

---

## 9. References

- `docs/synapse-rebrand-plan.md` — full inventory of every string that must
  change.
- `docs/architecture.md` §"Layer 1" — why we use Synapse at all.
- `infra/synapse/homeserver.yaml` — runtime config that complements this
  build-time overlay.
- Upstream: <https://github.com/element-hq/synapse>.
- AGPLv3: <https://www.gnu.org/licenses/agpl-3.0.html>.
