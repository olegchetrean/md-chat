# MD-Chat AI Layer — Testing Strategy

This directory contains the test suite for the `md_chat_ai` Python
package. The goal is fast, deterministic, hermetic tests that run on
every PR without external dependencies (Neo4j, Redis, Synapse, Infobip,
MPass, MSign, Router by MP).

## Layout

```
tests/
├── README.md                            # this file
├── conftest.py                          # shared fixtures (safe env, app, client)
├── test_health.py                       # legacy unit smoke (kept passing)
└── integration/
    ├── __init__.py
    ├── test_smoke_full_stack.py         # Flask boot + blueprint contract
    ├── test_compliance_disclosure.py    # AI Act Art 50 surface
    └── test_metrics.py                  # Prometheus exposition format
```

Each functional module (`auth/`, `identity/`, `eevidence/`, `agents/`,
`graph/`, `llm/`, `security/`, `reports/`) owns its own `tests/<module>/`
sub-tree of **unit** tests. The `integration/` directory here owns the
cross-module / blueprint / contract tests.

## Markers

| Marker         | Meaning                                                  |
|----------------|----------------------------------------------------------|
| `integration`  | Boots the Flask app via `create_app()`; slower than unit |
| `compliance`   | Regulatory check (AI Act, GDPR, MD Law 195/2024)         |
| `security`     | Security control verification (rate limit, prompt guard) |

Run subsets via `pytest -m "integration and not compliance"`, etc.

## Running

```bash
cd ai-layer
source .venv/bin/activate
pip install -e ".[dev]"

# All tests
pytest -q

# With coverage
pytest -q --cov=md_chat_ai --cov-report=term-missing

# Only integration
pytest -q -m integration

# Skip integration (fast inner loop)
pytest -q -m "not integration"
```

## Coverage policy

| Phase         | Target | Note                                                   |
|---------------|--------|--------------------------------------------------------|
| Sprint 0 (now)| 70%    | Bootstrap; only health.py + config.py exercised        |
| Sprint 1      | 80%    | Auth, identity, security modules covered               |
| Sprint 11     | 90%    | All modules + E2E + property-based tests for security  |

The CI workflow `ci.yml` fails the build below 70% to enforce the floor.

## Hermetic policy

Integration tests **MUST NOT** require:

- A running Neo4j server — use `mock_neo4j` fixture
- A running Redis — use `mock_redis` fixture
- Outbound HTTPS — patch with `responses` / `httpx_mock` / `respx`
- Real MPass / MSign endpoints — placeholder URLs in `conftest.SAFE_ENV`
- Real Router by MP key — placeholder env var

If a test needs a real backend, it belongs in the future `e2e/`
directory (Sprint 11), not here.

## Sibling-agent friendliness

Multiple feature agents are landing modules concurrently. The
integration tests are written so that a missing blueprint causes a
**skip**, not a **fail**:

```python
if "auth" not in app.blueprints:
    pytest.skip("auth blueprint not yet registered")
```

This keeps `main` green even when half the modules are still in flight.
Once an agent registers their blueprint, the corresponding integration
test starts asserting the contract automatically.

## Testing philosophy (one-paragraph version)

Unit tests prove a function does what its docstring says. Integration
tests prove the modules wire together. Security tests prove the system
refuses what it should refuse. Compliance tests prove that regulatory
obligations are observable from the running system, not buried in code
comments. End-to-end tests prove the user-visible journey works against
the real backends. We invest in the cheapest test that gives us the
proof we need, and we keep the suite fast enough that nobody is tempted
to skip it.
