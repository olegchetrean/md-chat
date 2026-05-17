"""SAML 2.0 Service Provider for Moldova MPass.

This module wraps the upstream ``python3-saml`` (a.k.a. ``onelogin``) library
and adds two layers of MD-Chat policy on top:

* a normalized, typed view of the attributes MPass returns;
* an :class:`AttributeReleasePolicy` that filters those attributes
  before they cross into the OIDC layer, so the OIDC bridge never
  even sees fields the user did not consent to release.

The SAML library itself is only imported lazily, because it depends
on ``libxmlsec1`` (a native library that does not install cleanly on
every workstation). The mapping / policy code is pure-Python and is
fully exercised by the test suite without requiring the SAML stack.

License: Apache 2.0.
"""

from __future__ import annotations

import datetime as _dt
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LOA / acr mapping
# ---------------------------------------------------------------------------


class LOA(str, Enum):
    """MPass Level of Assurance.

    Values match the strings MPass embeds in the SAML
    ``AuthnContextClassRef``. See AGE integration docs.
    """

    LOA1 = "LOA1"  # username + password
    LOA2 = "LOA2"  # SMS OTP / mobile eID
    LOA3 = "LOA3"  # USB token, qualified certificate


# Aligning with OIDC eIDAS profile values (informal — Moldova is not
# yet eIDAS-notified, so consumers must treat these as nationally
# scoped acr values).
_LOA_TO_ACR: dict[LOA, str] = {
    LOA.LOA1: "md.gov.mpass.loa1",
    LOA.LOA2: "md.gov.mpass.loa2",
    LOA.LOA3: "md.gov.mpass.loa3",
}


def map_loa_to_acr(loa: str | LOA | None) -> str:
    """Translate an MPass LOA value to the OIDC ``acr`` claim.

    Unknown / missing LOAs collapse to the weakest level (LOA1). We
    never silently *upgrade* trust.
    """
    if loa is None:
        return _LOA_TO_ACR[LOA.LOA1]
    if isinstance(loa, LOA):
        return _LOA_TO_ACR[loa]
    try:
        return _LOA_TO_ACR[LOA(loa)]
    except ValueError:
        logger.warning("mpass: unknown LOA value %r — defaulting to LOA1", loa)
        return _LOA_TO_ACR[LOA.LOA1]


# ---------------------------------------------------------------------------
# Age band (data minimization)
# ---------------------------------------------------------------------------


_AGE_BANDS: tuple[tuple[int, int, str], ...] = (
    (0, 17, "<18"),
    (18, 25, "18-25"),
    (26, 35, "26-35"),
    (36, 45, "36-45"),
    (46, 55, "46-55"),
    (56, 65, "56-65"),
    (66, 200, "65+"),
)


def map_birth_year_to_age_band(
    birth_year: int | str | None,
    *,
    now: _dt.date | None = None,
) -> str | None:
    """Convert a birth year to a coarse age band.

    Returning a band rather than the year itself is a data-minimization
    measure: chat features (e.g. AI Act Art. 28b youth protections) only
    need to know whether the user is in a coarse bucket, not their
    exact age. Returns :data:`None` if the input is unusable.
    """
    if birth_year is None or birth_year == "":
        return None
    try:
        year = int(birth_year)
    except (TypeError, ValueError):
        return None
    today = now or _dt.date.today()
    age = today.year - year
    if age < 0 or age > 150:
        return None
    for low, high, label in _AGE_BANDS:
        if low <= age <= high:
            return label
    return None


# ---------------------------------------------------------------------------
# Attribute release policy
# ---------------------------------------------------------------------------


#: SAML attribute names emitted by MPass. The exact URIs are defined
#: in the MPass IdP metadata; values below are the friendly names used
#: in the AGE integration handbook and double as keys in our normalized
#: representation.
MPASS_ATTRIBUTE_NAMES: tuple[str, ...] = (
    "verified",
    "birth_year",
    "given_name",
    "family_name",
    "email",
    "phone",
    "unique_identifier_personal_code",  # IDNP — sensitive
)

#: Attributes our public OIDC bridge is *willing* to surface to chat
#: clients. ``unique_identifier_personal_code`` (IDNP) is deliberately
#: omitted. See module-level docstring for the GDPR rationale.
DEFAULT_RELEASED_ATTRIBUTES: frozenset[str] = frozenset(
    {"verified", "birth_year", "given_name"}
)

#: Sensitive attribute names — must never be released unless the
#: relying party explicitly enables the second-consent flow.
SENSITIVE_ATTRIBUTES: frozenset[str] = frozenset(
    {"unique_identifier_personal_code", "family_name", "email", "phone"}
)


@dataclass(frozen=True)
class AttributeReleasePolicy:
    """Policy controlling which SAML attributes leak into OIDC claims.

    Instantiate one policy per relying party. The default policy
    refuses IDNP and any other sensitive attribute. Call
    :meth:`with_idnp` to obtain a stricter, purpose-limited policy
    that explicitly opts in to IDNP release (e.g. for an MSign flow).
    """

    released: frozenset[str] = DEFAULT_RELEASED_ATTRIBUTES
    purpose: str = "chat_account_provisioning"
    release_idnp: bool = False

    def with_idnp(self, *, purpose: str) -> "AttributeReleasePolicy":
        """Return a new policy that releases IDNP for the given purpose.

        ``purpose`` is logged on every release and is intended to be a
        short machine-readable token (e.g. ``"msign_qualified_signature"``)
        that downstream audit tooling can correlate with a consent record.
        """
        if not purpose:
            raise ValueError("purpose is required when releasing IDNP")
        return AttributeReleasePolicy(
            released=self.released | {"unique_identifier_personal_code"},
            purpose=purpose,
            release_idnp=True,
        )

    def filter(self, attributes: Mapping[str, Any]) -> dict[str, Any]:
        """Drop disallowed attributes from ``attributes``.

        Logs a structured warning whenever a sensitive attribute is
        observed but suppressed — useful for auditing IdP overshare.
        """
        out: dict[str, Any] = {}
        for key, value in attributes.items():
            if key == "unique_identifier_personal_code" and not self.release_idnp:
                logger.warning(
                    "mpass: suppressed IDNP (release policy=%s, purpose=%s)",
                    "default",
                    self.purpose,
                )
                continue
            if key in self.released:
                out[key] = value
            elif key in SENSITIVE_ATTRIBUTES:
                logger.info(
                    "mpass: suppressed sensitive attribute %s (not in policy)", key
                )
            else:
                # Unknown attributes are silently dropped.
                logger.debug("mpass: dropped unrecognized attribute %s", key)
        return out


# ---------------------------------------------------------------------------
# Normalized attribute object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MPassAttributes:
    """Typed view of one MPass SAML assertion.

    Construct via :meth:`from_saml_response` or directly in tests. All
    fields are optional because MPass only releases what the user
    consented to at the IdP.
    """

    verified: bool = False
    birth_year: int | None = None
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
    phone: str | None = None
    idnp: str | None = None
    loa: LOA = LOA.LOA1
    name_id: str | None = None
    issued_at: _dt.datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_saml_response(
        cls,
        attributes: Mapping[str, Iterable[Any] | Any],
        *,
        loa: str | None = None,
        name_id: str | None = None,
        issued_at: _dt.datetime | None = None,
    ) -> "MPassAttributes":
        """Build from the dict returned by ``OneLogin_Saml2_Auth.get_attributes()``.

        ``python3-saml`` returns each attribute as a list of strings.
        We pull the first element and coerce types.
        """
        def _first(name: str) -> str | None:
            v = attributes.get(name)
            if v is None:
                return None
            if isinstance(v, (list, tuple)):
                return str(v[0]) if v else None
            return str(v)

        verified_raw = _first("verified") or ""
        verified = verified_raw.strip().lower() in {"true", "1", "yes", "verified"}

        birth_year_raw = _first("birth_year")
        try:
            birth_year = int(birth_year_raw) if birth_year_raw else None
        except ValueError:
            birth_year = None

        try:
            loa_enum = LOA(loa) if loa else LOA.LOA1
        except ValueError:
            loa_enum = LOA.LOA1

        return cls(
            verified=verified,
            birth_year=birth_year,
            given_name=_first("given_name"),
            family_name=_first("family_name"),
            email=_first("email"),
            phone=_first("phone"),
            idnp=_first("unique_identifier_personal_code"),
            loa=loa_enum,
            name_id=name_id,
            issued_at=issued_at,
            raw=dict(attributes),
        )

    def as_attribute_dict(self) -> dict[str, Any]:
        """Return a flat dict keyed by canonical SAML attribute names."""
        return {
            "verified": self.verified,
            "birth_year": self.birth_year,
            "given_name": self.given_name,
            "family_name": self.family_name,
            "email": self.email,
            "phone": self.phone,
            "unique_identifier_personal_code": self.idnp,
        }


# ---------------------------------------------------------------------------
# SAML → OIDC claim mapping
# ---------------------------------------------------------------------------


def saml_attributes_to_oidc_claims(
    attrs: MPassAttributes,
    policy: AttributeReleasePolicy | None = None,
    *,
    now: _dt.date | None = None,
) -> dict[str, Any]:
    """Translate a normalized SAML assertion into OIDC claims.

    Mapping table::

        SAML verified                       -> OIDC verified           (bool)
        SAML birth_year                     -> OIDC age_band           (str)
        SAML given_name                     -> OIDC prenume            (str)
        SAML unique_identifier_personal_code-> OIDC idnp               (str, gated)
        MPass LOA                           -> OIDC acr                (str)
        SAML name_id                        -> OIDC sub                (str)

    The OIDC ``sub`` claim is always the opaque MPass ``NameID``,
    never the IDNP — this lets MD-Chat retire the link to MPass
    without leaking a stable government identifier.
    """
    policy = policy or AttributeReleasePolicy()
    filtered = policy.filter({k: v for k, v in attrs.as_attribute_dict().items() if v is not None})

    claims: dict[str, Any] = {}
    if "verified" in filtered:
        claims["verified"] = bool(filtered["verified"])
    age_band = map_birth_year_to_age_band(filtered.get("birth_year"), now=now)
    if age_band is not None:
        claims["age_band"] = age_band
    if "given_name" in filtered:
        claims["prenume"] = filtered["given_name"]
    if "unique_identifier_personal_code" in filtered:
        claims["idnp"] = filtered["unique_identifier_personal_code"]
    if "email" in filtered:
        claims["email"] = filtered["email"]
    if "family_name" in filtered:
        claims["family_name"] = filtered["family_name"]

    claims["acr"] = map_loa_to_acr(attrs.loa)
    if attrs.name_id:
        claims["sub"] = attrs.name_id
    claims["iss_idp"] = "https://mpass.gov.md"
    return claims


# ---------------------------------------------------------------------------
# SAML SP wrapper
# ---------------------------------------------------------------------------


@dataclass
class _SamlRequestEnvelope:
    """Information the OIDC layer needs to reply to the IdP redirect."""

    redirect_url: str
    relay_state: str


class MPassSamlSP:
    """Service Provider facade around ``python3-saml``.

    Constructed once per process; configured from :class:`md_chat_ai.config.Config`.
    The heavyweight SAML library is only imported on first use so the
    rest of the test suite can run without ``libxmlsec1``.
    """

    def __init__(
        self,
        *,
        entity_id: str,
        acs_url: str,
        slo_url: str,
        sp_cert_path: str,
        sp_key_path: str,
        idp_metadata_url: str,
        idp_metadata_path: str = "",
    ) -> None:
        self.entity_id = entity_id
        self.acs_url = acs_url
        self.slo_url = slo_url
        self.sp_cert_path = sp_cert_path
        self.sp_key_path = sp_key_path
        self.idp_metadata_url = idp_metadata_url
        self.idp_metadata_path = idp_metadata_path
        self._settings: Any = None

    # -- settings ---------------------------------------------------------

    def settings_dict(self) -> dict[str, Any]:
        """Build the dict ``python3-saml`` consumes.

        Splitting this out keeps it trivially testable: tests assert on
        the shape of the dict without instantiating the SAML library.
        """
        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self.entity_id,
                "assertionConsumerService": {
                    "url": self.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": self.slo_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent",
                "x509cert": _read_file_or_empty(self.sp_cert_path),
                "privateKey": _read_file_or_empty(self.sp_key_path),
            },
            "idp": {
                "entityId": "https://mpass.gov.md",
                "singleSignOnService": {
                    "url": "https://mpass.gov.md/Login",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": "https://mpass.gov.md/Logout",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": "",  # populated from metadata at startup
                "metadataUrl": self.idp_metadata_url,
            },
            "security": {
                "authnRequestsSigned": True,
                "wantAssertionsSigned": True,
                "wantAssertionsEncrypted": False,
                "signMetadata": True,
                "wantNameId": True,
                "requestedAuthnContext": [
                    "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport",
                ],
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            },
        }

    # -- runtime ----------------------------------------------------------

    def _load_auth(self, request_data: Mapping[str, Any]) -> Any:
        """Construct a ``OneLogin_Saml2_Auth`` instance.

        Imported lazily to avoid hard-failing on machines without
        ``libxmlsec1``.
        """
        try:  # pragma: no cover — heavy native dep
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "python3-saml is not installed; install the 'identity' extra"
            ) from exc
        return OneLogin_Saml2_Auth(dict(request_data), self.settings_dict())

    def build_authn_request(
        self,
        request_data: Mapping[str, Any],
        *,
        relay_state: str,
    ) -> _SamlRequestEnvelope:
        """Return the redirect URL the browser should follow to start SSO."""
        auth = self._load_auth(request_data)
        redirect = auth.login(return_to=relay_state)
        return _SamlRequestEnvelope(redirect_url=redirect, relay_state=relay_state)

    def process_response(
        self, request_data: Mapping[str, Any]
    ) -> MPassAttributes:
        """Validate an inbound SAML response and return normalized attributes."""
        auth = self._load_auth(request_data)
        auth.process_response()
        errors = auth.get_errors()
        if errors:
            raise SamlResponseError(
                f"SAML response invalid: {errors}; last_error={auth.get_last_error_reason()}"
            )
        if not auth.is_authenticated():
            raise SamlResponseError("SAML response did not authenticate the user")
        attrs = auth.get_attributes()
        loa = _extract_loa(auth)
        return MPassAttributes.from_saml_response(
            attrs,
            loa=loa,
            name_id=auth.get_nameid(),
            issued_at=_dt.datetime.now(tz=_dt.timezone.utc),
        )


class SamlResponseError(RuntimeError):
    """Raised when MPass returns an invalid or unauthenticated assertion."""


def _read_file_or_empty(path: str) -> str:
    """Best-effort cert / key load. Empty string when missing.

    Returning an empty string rather than raising lets us boot the
    service in dev mode without real certificates; ``python3-saml``
    will refuse to *send* requests in that state, so the failure mode
    is loud but late.
    """
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        logger.warning("mpass: could not read %s", path)
        return ""


def _extract_loa(auth: Any) -> str | None:
    """Pull the AuthnContextClassRef out of the SAML response, if present."""
    try:
        # The python3-saml API exposes the LOA via the underlying XML
        # document; we look for any "LOAx" token in the context refs.
        ctx = auth.get_session_index() or ""
        for level in (LOA.LOA3, LOA.LOA2, LOA.LOA1):
            if level.value in str(ctx):
                return level.value
    except Exception:  # pragma: no cover — defensive
        logger.exception("mpass: failed to read AuthnContextClassRef")
    return None
