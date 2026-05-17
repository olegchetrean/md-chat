# MD-Chat — Release Process

This document is the **single source of truth** for cutting an MD-Chat
release. It covers the AI layer (Python package + Docker image) and is
the template for the other components (server, clients) once they ship.

## Versioning policy

MD-Chat follows **SemVer 2.0.0** (`MAJOR.MINOR.PATCH`):

| Bump   | When                                                            |
|--------|-----------------------------------------------------------------|
| MAJOR  | Backwards-incompatible API change in `/api/v1/*` or DB schema   |
| MINOR  | New backwards-compatible feature (new endpoint, new agent, etc.)|
| PATCH  | Bug fixes, security patches, dependency updates, docs           |

Pre-releases use the `-alpha.N`, `-beta.N`, `-rc.N` suffixes:
`v0.2.0-rc.1`, etc.

### Tag format

All tags are prefixed with `v`. The CI release workflow only matches
the pattern `v[0-9]+.[0-9]+.[0-9]+(-*)?`:

```
v0.1.0          # GA
v0.2.0-rc.1     # release candidate
v0.2.0-alpha.3  # alpha
```

The `pyproject.toml` `version` field MUST match the tag minus the `v`
prefix. The release workflow refuses to publish on mismatch.

## Pre-release checklist

Before pushing a release tag, the release captain (Oleg) runs through:

- [ ] All sibling-agent PRs merged or explicitly deferred.
- [ ] `pyproject.toml` version bumped, committed on `main`.
- [ ] `CHANGELOG.md` (when it exists) updated; otherwise rely on
      auto-generated git-log notes from the `release.yml` workflow.
- [ ] CI green on `main` for the commit being released.
- [ ] `pytest --cov=md_chat_ai --cov-fail-under=70` passes locally.
- [ ] `bandit -r ai-layer/src -ll` reports no HIGH severity issues.
- [ ] `pip-audit` reports no unfixed criticals.
- [ ] `trivy image md-chat-ai:latest --severity CRITICAL,HIGH` clean.
- [ ] SBOM generated locally and reviewed for unexpected components.
- [ ] Compliance checklist:
      - [ ] AI Act Art 50 disclosure strings unchanged (or, if changed,
            change reviewed by counsel).
      - [ ] GDPR data-minimisation defaults preserved
            (`MPASS_RELEASE_IDNP=false`, OIDC HTTPS issuer).
      - [ ] CRA — SBOM workflow tested on a prior tag.
- [ ] Docker image builds and `/api/health` returns 200 in a smoke
      container.

## Cutting a release

### Option A — tag push (preferred for regular releases)

```bash
# Bump version in pyproject.toml, commit
git switch main
git pull origin main

# Edit ai-layer/pyproject.toml: version = "0.2.0"
git add ai-layer/pyproject.toml
git commit -m "release: 0.2.0"
git push origin main

# Wait for CI green, then tag.
git tag -s v0.2.0 -m "MD-Chat AI Layer 0.2.0"  # -s = signed (once GPG ready)
git push origin v0.2.0
```

The tag push triggers:
1. `release.yml` — validates semver, builds sdist+wheel, drafts notes,
   creates a GitHub Release (draft by default).
2. `sbom.yml` — generates CycloneDX SBOMs for the Python package and
   the container image, attaches them to the release.

### Option B — manual dispatch (for hotfixes or first release)

GitHub Actions → "Release" workflow → "Run workflow":
- `version`: `0.2.0`
- `prerelease`: false
- `draft`: true

Same downstream steps execute; the workflow won't create a tag for
you — you still need to push `v0.2.0` afterwards if you want SBOMs.

## Release artefacts

Every release publishes:

| Artefact                              | Source workflow | Format             |
|---------------------------------------|-----------------|--------------------|
| `md_chat_ai-X.Y.Z.tar.gz`             | `release.yml`   | Python sdist       |
| `md_chat_ai-X.Y.Z-py3-none-any.whl`   | `release.yml`   | Python wheel       |
| `md-chat-ai-sbom.cdx.json`            | `sbom.yml`      | CycloneDX JSON 1.5 |
| `md-chat-ai-sbom.cdx.xml`             | `sbom.yml`      | CycloneDX XML 1.5  |
| `md-chat-ai-image-sbom.cdx.json`      | `sbom.yml`      | Container SBOM     |
| `release-notes.md`                    | `release.yml`   | Markdown changelog |

## Signing — current status

**Today:** releases are NOT cryptographically signed.

**Sprint 2 target:** Oleg generates a GPG key dedicated to
`releases@md-chat.eu`, publishes the public key to
`https://md-chat.eu/release-key.asc` and to keys.openpgp.org, and:

- `git tag -s vX.Y.Z` produces signed tags.
- A `cosign` keyless signature attests the SBOMs and container images.
- The `release.yml` workflow runs `gpg --verify` on the tag before
  publishing.

Until then, release notes call out that artefacts are **unsigned** and
that downstream consumers should pin by digest, not by tag.

## Hotfix process

1. Branch from the latest release tag: `git switch -c hotfix/0.1.1 v0.1.0`.
2. Cherry-pick the fix commits or write the patch.
3. Bump `pyproject.toml` to `0.1.1`.
4. Open a PR targeting `main`; CI must pass.
5. Merge to `main`; tag `v0.1.1`; push tag.
6. Backport docs / changelog notes to `main` if not already there.

## Yank / rollback policy

Releases are never deleted. If a release contains a security issue:

1. Tag a new patch release (`v0.1.2`) with the fix.
2. Edit the bad release's GitHub Release notes prepending a banner:

   > **DEPRECATED — security issue CVE-YYYY-NNNNN. Upgrade to vX.Y.Z.**

3. Optionally yank from PyPI (when we publish there) using
   `twine yank`.
4. File an advisory under GitHub Security Advisories.

## Component-specific notes

### AI layer (this doc)

Python package + Docker image. Both ship every release.

### Synapse server, native clients, web client

Deferred to Sprint 4. They will follow the same SemVer + tag-push
pattern. The CRA SBOM requirement extends to those components as soon
as they start shipping binaries.

### Infrastructure (`infra/`)

Not released; tracked by commit SHA in deploy manifests.
