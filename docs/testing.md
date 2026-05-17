# MD-Chat — Testing Philosophy

This document describes how we test MD-Chat across all components
(AI layer, server, native clients, web client, infrastructure). It is
the **policy** document; the AI-layer-specific *how* lives in
[`ai-layer/tests/README.md`](../ai-layer/tests/README.md).

## Principles

1. **Tests are how we communicate intent.** A test that exists tells the
   next engineer what the system promises. A test that's missing tells
   them they're on their own.
2. **The cheapest test that gives us the proof we need.** Unit beats
   integration beats E2E when the proof is equivalent. Property-based
   beats example-based when the invariant is universal.
3. **Hermetic by default.** A test that fails because someone's laptop
   doesn't have Neo4j running is a broken test, not a flaky test. Mock
   external dependencies; reserve real-backend tests for the `e2e/`
   directory.
4. **Fast inner loop.** The whole unit + integration suite MUST run in
   under 60 seconds locally. If it doesn't, we split it.
5. **CI is the only authority.** Local "it works for me" doesn't count.
   The CI workflow `ci.yml` is the source of truth for `passing`.
6. **Compliance is a test, not a comment.** Regulatory obligations
   (AI Act Art 50, GDPR Art 5, CRA Annex I) are encoded as failing
   tests when violated. Lawyers read tests, not changelogs.

## The five test layers

### 1. Unit tests (per-module)

- **Owned by:** the module author.
- **Location:** `ai-layer/tests/<module>/test_<file>.py`.
- **Scope:** one function or class, all branches, no I/O.
- **Mock everything** — Neo4j, Redis, HTTP, time, randomness.
- **Coverage floor:** 80% per module (90% for `auth/`, `security/`,
  `identity/`).

### 2. Integration tests (cross-module, in-process)

- **Owned by:** the test-infrastructure agent (this PR).
- **Location:** `ai-layer/tests/integration/`.
- **Scope:** boots the Flask app via `create_app()`, hits HTTP routes
  with the Flask test client.
- **Skip-friendly:** if a blueprint is missing (sibling agent not done
  yet), the test SKIPS, it does not FAIL.
- **No real Neo4j / Redis / Synapse / Infobip.**

### 3. Security tests (control verification)

- **Owned by:** security-module author + this PR.
- **Location:** `ai-layer/tests/integration/test_*security*.py` plus
  `bandit` SAST and `pip-audit` / `safety` SCA in CI.
- **Scope:** assert the system *refuses* what it should refuse
  (rate-limit triggers, prompt injection rejected, IDNP not released
  without consent, weak JWT signatures rejected).
- **Marker:** `@pytest.mark.security`.

### 4. Compliance tests (regulatory)

- **Owned by:** this PR + every feature that touches a regulatory
  surface.
- **Location:** `ai-layer/tests/integration/test_compliance_*.py`.
- **Scope:** verify that the running system exposes the disclosures and
  defaults required by:
  - **EU AI Act** (Regulation (EU) 2024/1689) Art 50 — transparency to
    natural persons.
  - **GDPR** (Regulation (EU) 2016/679) Art 5(1)(c) — data minimisation,
    Art 7 — separable consent.
  - **MD Law 195/2024** — Moldova's AI Act-aligned national law,
    enters into force 23 Aug 2026.
  - **CRA** (Regulation (EU) 2024/2847) Annex I §2 — SBOM, vulnerability
    handling, secure-by-default.
- **Marker:** `@pytest.mark.compliance`.

### 5. End-to-end (E2E) tests (deferred to Sprint 11)

- **Owned by:** QA lead (TBD).
- **Location:** `e2e/` (top-level; spans server + ai-layer + clients).
- **Scope:** real Synapse, real Neo4j, real Router by MP test key,
  real Infobip sandbox. Exercises full user journeys (register → MFA
  → chat with AI agent → request E-Evidence export).
- **When:** runs nightly on a dedicated test environment, not on PR.

## Coverage targets

| Phase         | Coverage | Notes                                                |
|---------------|----------|------------------------------------------------------|
| Sprint 0 (now)| 70%      | Bootstrap; only `health.py` + `config.py` exercised  |
| Sprint 1      | 80%      | Auth, identity, security modules covered             |
| Sprint 4      | 85%      | LLM, agents, graph modules covered                   |
| Sprint 11     | 90%      | All modules + E2E + mutation testing                 |

The CI workflow `ci.yml` enforces the floor: PRs that drop coverage
below 70% are blocked.

## How to add a test

1. Identify the layer (unit / integration / security / compliance).
2. Pick the right marker (`integration`, `security`, `compliance`).
3. Write the test as **arrange–act–assert**, one assertion per logical
   claim.
4. Run it locally: `pytest -q path/to/test_file.py`.
5. Open a PR. CI runs ruff + black + mypy + pytest + coverage + bandit
   + safety + pip-audit + trivy.
6. The PR is reviewed against [`docs/release-process.md`](release-process.md)
   gates before merging.

## Anti-patterns we reject

- **Snapshot-only tests** of business logic (snapshot is fine for
  generated artefacts like OpenAPI schemas — not for logic).
- **Tests that sleep.** Use clock injection.
- **Tests that depend on test order.** Each test must work in isolation.
- **Tests against production endpoints.** Use Router by MP test keys
  or recorded fixtures.
- **`assert True` placeholders.** Either write the assertion or skip
  the test with a reason.
- **Disabling a test to make CI green.** Either fix it or delete it
  with a documented reason in the PR.

## Reading list

- "How to design tests that don't break when you refactor" — Kent C. Dodds
- "Property-based testing with Hypothesis" — David R. MacIver
- "Working Effectively with Legacy Code" — Michael Feathers (ch. 5–10)
