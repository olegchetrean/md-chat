"""SOAP client for Moldova MSign qualified-signature service.

MSign is the AGE-operated SOAP service that produces a qualified
electronic signature on a PDF or PKCS#7 envelope. The official WSDL is
published at https://msign.gov.md/services/sign?wsdl.

This module wraps the SOAP call in a small REST-friendly API:

>>> client = MSignClient.from_config(CONFIG)
>>> result = client.sign(SignatureRequest(document=pdf_bytes, mime_type="application/pdf"))
>>> result.signed_document  # bytes

It also provides a synchronous ``health`` probe and a hook for swapping
``zeep``'s transport during tests.

License: Apache 2.0.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignatureRequest:
    """Payload for a single signature request."""

    document: bytes
    mime_type: str = "application/pdf"
    purpose: str = "md-chat-msign"
    visible: bool = False
    language: str = "ro"

    def as_soap_payload(self, *, client_id: str) -> dict[str, Any]:
        """Render to the dict shape ``zeep`` expects.

        The WSDL element names below match the public MSign contract
        as documented in the AGE integration handbook (v1.2). They
        are duplicated here so the test suite can assert the wire
        format without instantiating ``zeep``.
        """
        return {
            "ClientID": client_id,
            "Document": {
                "Content": base64.b64encode(self.document).decode("ascii"),
                "ContentType": self.mime_type,
                "Language": self.language,
            },
            "SignatureOptions": {
                "Visible": self.visible,
                "Purpose": self.purpose,
            },
        }


@dataclass(frozen=True)
class SignatureResult:
    """Successful response from MSign."""

    signed_document: bytes
    signature_id: str
    certificate_chain: tuple[str, ...] = ()
    raw: Mapping[str, Any] | None = None

    @classmethod
    def from_soap_response(cls, response: Mapping[str, Any]) -> "SignatureResult":
        """Parse the SOAP body MSign returns.

        Accepts both the snake_case form ``zeep`` normalizes to and the
        PascalCase form found in the WSDL — robust against future MSign
        revisions.
        """
        signed_b64 = (
            response.get("SignedDocument")
            or response.get("signed_document")
            or response.get("Content")
        )
        if signed_b64 is None:
            raise MSignError("MSign response missing SignedDocument")
        try:
            signed = base64.b64decode(signed_b64)
        except (TypeError, ValueError) as exc:
            raise MSignError("MSign response not base64") from exc
        sig_id = (
            response.get("SignatureID")
            or response.get("signature_id")
            or response.get("Id", "")
        )
        chain_raw = (
            response.get("CertificateChain")
            or response.get("certificate_chain")
            or []
        )
        if isinstance(chain_raw, str):
            chain: tuple[str, ...] = (chain_raw,)
        else:
            chain = tuple(chain_raw)
        return cls(
            signed_document=signed,
            signature_id=str(sig_id),
            certificate_chain=chain,
            raw=dict(response),
        )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class MSignError(RuntimeError):
    """Raised for any MSign protocol or transport failure."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


#: Type alias for a callable that takes the SOAP payload and returns
#: the SOAP response body. Tests pass in fakes here so we never have
#: to spin up ``zeep`` for unit testing.
SoapInvoker = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class MSignClient:
    """Thin SOAP wrapper.

    Parameters
    ----------
    wsdl_url:
        URL of the MSign WSDL.
    client_id:
        ID issued by AGE during onboarding (mandatory in the SOAP
        envelope's ``ClientID`` element).
    client_secret:
        Shared secret used in HTTP Basic auth against the SOAP
        endpoint.
    timeout:
        Per-call timeout (seconds).
    invoker:
        Test seam — pass a callable to bypass ``zeep`` entirely.
        ``None`` causes the client to lazily build a ``zeep.Client``.
    """

    def __init__(
        self,
        *,
        wsdl_url: str,
        client_id: str,
        client_secret: str = "",
        timeout: int = 30,
        invoker: SoapInvoker | None = None,
    ) -> None:
        self.wsdl_url = wsdl_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._invoker = invoker
        self._zeep_client: Any = None

    # -- construction helpers -------------------------------------------

    @classmethod
    def from_config(cls, config: Any, *, invoker: SoapInvoker | None = None) -> "MSignClient":
        return cls(
            wsdl_url=config.msign_wsdl_url,
            client_id=config.msign_client_id,
            client_secret=config.msign_client_secret,
            timeout=config.msign_timeout,
            invoker=invoker,
        )

    # -- API ------------------------------------------------------------

    def sign(self, request: SignatureRequest) -> SignatureResult:
        """Send a single document through MSign and return the signed bytes."""
        if not self.client_id:
            raise MSignError("MSIGN_CLIENT_ID is not configured")
        payload = request.as_soap_payload(client_id=self.client_id)
        try:
            response = self._invoke("Sign", payload)
        except MSignError:
            raise
        except Exception as exc:
            raise MSignError(f"MSign transport failure: {exc!s}") from exc
        if not isinstance(response, Mapping):
            raise MSignError(f"unexpected MSign response type: {type(response)!r}")
        return SignatureResult.from_soap_response(response)

    def health(self) -> bool:
        """Best-effort health probe (returns True if WSDL is loadable)."""
        try:
            self._ensure_zeep()
            return True
        except Exception:
            logger.exception("msign: health probe failed")
            return False

    # -- internals ------------------------------------------------------

    def _invoke(self, operation: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if self._invoker is not None:
            return self._invoker(payload)
        zc = self._ensure_zeep()
        service = zc.service  # type: ignore[attr-defined]
        method = getattr(service, operation, None)
        if method is None:
            raise MSignError(f"MSign WSDL does not expose operation {operation!r}")
        return method(**payload)

    def _ensure_zeep(self) -> Any:
        if self._zeep_client is not None:
            return self._zeep_client
        try:  # pragma: no cover — heavy dep, exercised via fakes in tests
            from zeep import Client
            from zeep.transports import Transport
        except ImportError as exc:  # pragma: no cover
            raise MSignError(
                "zeep is not installed; install the 'identity' extra"
            ) from exc
        transport = Transport(timeout=self.timeout)
        self._zeep_client = Client(self.wsdl_url, transport=transport)
        return self._zeep_client
