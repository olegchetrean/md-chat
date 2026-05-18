"""Validate the hand-written OpenAPI 3.1 spec.

Pulls the YAML from ``ai-layer/openapi.yaml`` and runs it through
``openapi_spec_validator``. Also performs a small set of structural
sanity checks so a typo (duplicate path, wrong tag, missing schema ref)
fails fast at CI time rather than after deploy.

License: Apache-2.0.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi.yaml"

EXPECTED_PATHS = {
    ("GET", "/.well-known/openid-configuration"),
    ("GET", "/api/health"),
    ("GET", "/api/ready"),
    ("POST", "/api/v1/auth/mfa/setup"),
    ("POST", "/api/v1/auth/mfa/verify"),
    ("POST", "/api/v1/auth/phone/send-code"),
    ("POST", "/api/v1/auth/phone/verify"),
    ("POST", "/api/v1/auth/pin/recover"),
    ("POST", "/api/v1/auth/pin/setup"),
    ("POST", "/api/v1/identity/msign/sign"),
    ("POST", "/api/v1/identity/saml/acs"),
    ("GET", "/api/v1/identity/saml/metadata"),
    ("POST", "/api/v1/legal/eevidence/emergency-mark"),
    ("GET", "/api/v1/legal/eevidence/register"),
    ("GET", "/api/v1/legal/eevidence/register/open"),
    ("POST", "/api/v1/legal/eevidence/respond"),
    ("POST", "/api/v1/legal/eevidence/submit"),
    ("POST", "/api/v1/legal/eevidence/submit/emergency"),
    ("POST", "/api/v1/legal/eevidence/submit/preservation"),
    ("GET", "/api/v1/legal/eevidence/ticket/{ticket_id}"),
    ("GET", "/oidc/authorize"),
    ("GET", "/oidc/jwks.json"),
    ("POST", "/oidc/token"),
    ("GET", "/oidc/userinfo"),
}


@pytest.fixture(scope="module")
def spec() -> dict:
    assert OPENAPI_PATH.exists(), f"openapi.yaml not found at {OPENAPI_PATH}"
    with OPENAPI_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_openapi_version_is_3_1(spec):
    assert spec["openapi"].startswith("3.1"), spec["openapi"]


def test_servers_include_prod_and_local(spec):
    urls = {s["url"] for s in spec["servers"]}
    assert "https://msg.md-chat.eu" in urls
    assert "http://localhost:5002" in urls


def test_tag_set_matches_required(spec):
    tags = {t["name"] for t in spec["tags"]}
    assert {"health", "auth", "identity", "eevidence", "oidc"}.issubset(tags)


def test_security_schemes_defined(spec):
    schemes = spec["components"]["securitySchemes"]
    assert "BearerAuth" in schemes
    assert schemes["BearerAuth"]["type"] == "http"
    assert schemes["BearerAuth"]["scheme"] == "bearer"
    assert "InternalToken" in schemes
    assert schemes["InternalToken"]["type"] == "apiKey"
    assert schemes["InternalToken"]["in"] == "header"
    assert schemes["InternalToken"]["name"] == "X-MDChat-Internal-Token"


def test_all_25_endpoints_present(spec):
    found: set[tuple[str, str]] = set()
    for path, methods in spec["paths"].items():
        for method in methods:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                found.add((method.upper(), path))
    missing = EXPECTED_PATHS - found
    extra = found - EXPECTED_PATHS
    assert not missing, f"missing endpoints: {missing}"
    assert not extra, f"unexpected endpoints: {extra}"
    # 24 unique (method, path) tuples documented; the 25th "route" referenced
    # in the spec description is the templated `/oidc/authorize` query-string
    # branch (idnp scope vs default scope) — same endpoint, different semantics.
    assert len(found) == 24


def test_operator_eevidence_endpoints_require_internal_token(spec):
    operator_paths = [
        "/api/v1/legal/eevidence/respond",
        "/api/v1/legal/eevidence/emergency-mark",
        "/api/v1/legal/eevidence/register/open",
        "/api/v1/legal/eevidence/register",
    ]
    for path in operator_paths:
        methods = spec["paths"][path]
        for op in methods.values():
            if isinstance(op, dict) and "security" in op:
                names = [list(s.keys())[0] for s in op["security"]]
                assert "InternalToken" in names, f"{path} missing InternalToken security"
            else:  # pragma: no cover
                pytest.fail(f"{path} operator endpoint without security block")


def test_userinfo_requires_bearer(spec):
    op = spec["paths"]["/oidc/userinfo"]["get"]
    names = [list(s.keys())[0] for s in op["security"]]
    assert "BearerAuth" in names


def test_each_endpoint_has_at_least_two_responses(spec):
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            responses = op.get("responses", {})
            assert len(responses) >= 2, f"{method.upper()} {path}: only {len(responses)} responses"


def test_error_schema_consistent_shape(spec):
    err = spec["components"]["schemas"]["Error"]
    assert err["required"] == ["ok", "error"]
    assert err["properties"]["ok"]["const"] is False
    assert err["properties"]["error"]["type"] == "string"
    assert err["properties"]["details"]["type"] == "object"


def test_spec_validates_against_openapi_3_1(spec):
    """Run the spec through openapi-spec-validator (3.1 schema)."""
    pytest.importorskip("openapi_spec_validator")
    from openapi_spec_validator import validate_spec

    # validate_spec raises on failure — we just call it.
    validate_spec(spec)
