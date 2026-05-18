"""Internationalization for MD-Chat AI layer.

Public API
----------
* :func:`translate` — look up a key for a language, with English fallback.
* :func:`negotiate_language` — RFC 4647 Accept-Language matching.
* :func:`available_languages` — supported base codes.
* :func:`reload` — re-read JSON translation files (test hook).

Scope
-----
Sprint 0 plumbing: flat-dict JSON catalog, ``str.format`` placeholder
interpolation, no plurals / genders / ICU. The 3-language hardcoded
AI Act Art 50 disclosure in ``config.py`` will be migrated to this module
in a follow-up sprint — this module does not yet rewrite any API
endpoint behavior.

Example
-------
>>> from md_chat_ai.i18n import translate, negotiate_language
>>> translate("welcome.title", lang="ro")
'Bine ați venit pe MD-Chat'
>>> negotiate_language({"Accept-Language": "ro-MD,ro;q=0.9,en;q=0.7"})
'ro'
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .catalog import (
    FALLBACK_LANGUAGE,
    SUPPORTED_LANGUAGES,
    available_languages,
    get_catalog,
    normalize_language,
    reload,
)

__all__ = [
    "translate",
    "negotiate_language",
    "available_languages",
    "reload",
    "SUPPORTED_LANGUAGES",
    "FALLBACK_LANGUAGE",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# translate()
# ---------------------------------------------------------------------------


def translate(key: str, lang: str = FALLBACK_LANGUAGE, /, **kwargs: Any) -> str:
    """Resolve ``key`` in ``lang``, falling back to English then to the key itself.

    Placeholder substitution uses Python's :py:meth:`str.format` — keep
    placeholders simple (``{name}``, not ICU MessageFormat).

    Parameters
    ----------
    key:
        Dotted-namespace translation key, e.g. ``auth.phone.code_sent``.
    lang:
        Target language code. Accepts regional variants (``ro-MD``,
        ``ru_RU``) — these are normalized via :func:`normalize_language`.
    **kwargs:
        Placeholder values for ``str.format`` interpolation.

    Returns
    -------
    str
        The translated, interpolated string. If interpolation fails
        (missing/extra placeholder), the raw template is returned and a
        warning is logged — i18n must not crash the API.
    """
    base_lang = normalize_language(lang)
    catalog = get_catalog()

    template = catalog.get(base_lang, {}).get(key)
    if template is None and base_lang != FALLBACK_LANGUAGE:
        template = catalog.get(FALLBACK_LANGUAGE, {}).get(key)
        if template is not None:
            logger.debug("i18n: key %r missing in %s, used %s fallback", key, base_lang, FALLBACK_LANGUAGE)

    if template is None:
        logger.warning("i18n: key %r missing in %s and %s", key, base_lang, FALLBACK_LANGUAGE)
        return key

    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("i18n: format failed for key %r lang=%s: %s", key, base_lang, exc)
        return template


# ---------------------------------------------------------------------------
# negotiate_language()
# ---------------------------------------------------------------------------


# RFC 7231 / RFC 4647: language-range [ ";q=" weight ]
_LANG_RE = re.compile(r"^\s*([A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*|\*)\s*(?:;\s*q\s*=\s*([0-9.]+)\s*)?$")


def _parse_accept_language(header: str) -> list[tuple[str, float]]:
    """Parse an Accept-Language header into ``[(tag, q), ...]`` sorted by q.

    Invalid items are skipped. Items with no explicit ``q`` get q=1.0.
    Stable sort preserves original order among equal-q items, matching
    the precedence rule in RFC 4647 §3.4.
    """
    entries: list[tuple[int, str, float]] = []
    for idx, raw in enumerate(header.split(",")):
        match = _LANG_RE.match(raw)
        if not match:
            continue
        tag, q = match.group(1), match.group(2)
        try:
            weight = float(q) if q is not None else 1.0
        except ValueError:
            weight = 1.0
        if weight <= 0:  # q=0 means "not acceptable"
            continue
        entries.append((idx, tag.lower(), weight))

    # Sort by descending q, then by original order for ties.
    entries.sort(key=lambda t: (-t[2], t[0]))
    return [(tag, q) for _, tag, q in entries]


def negotiate_language(request: Any) -> str:
    """Pick the best-matching supported language for an HTTP request.

    Accepts:

    * a Flask / Werkzeug ``Request`` (uses ``request.headers``),
    * a plain ``dict`` of headers,
    * a raw ``str`` Accept-Language header value,
    * ``None`` / empty (returns the fallback).

    Matching follows RFC 4647 lookup-style: try the full tag, then strip
    the last ``-`` subtag, until something matches our supported set.
    ``*`` matches the fallback language.
    """
    header = _extract_accept_language(request)
    if not header:
        return FALLBACK_LANGUAGE

    for tag, _q in _parse_accept_language(header):
        if tag == "*":
            return FALLBACK_LANGUAGE
        # Try progressively shorter prefixes: ro-md -> ro.
        candidate = tag
        while candidate:
            normalized = normalize_language(candidate)
            if normalized in SUPPORTED_LANGUAGES and (
                candidate in SUPPORTED_LANGUAGES or candidate in {a.lower() for a in _aliases_for(normalized)}
            ):
                return normalized
            # Allow base-language match: ``ro-foo`` -> ``ro`` even if
            # ``ro-foo`` is not explicitly aliased.
            base = candidate.split("-", 1)[0]
            if base in SUPPORTED_LANGUAGES:
                return base
            if "-" not in candidate:
                break
            candidate = candidate.rsplit("-", 1)[0]

    return FALLBACK_LANGUAGE


def _aliases_for(base: str) -> list[str]:
    """Return regional aliases that map to ``base`` (for completeness checks)."""
    from .catalog import REGIONAL_ALIASES

    return [alias for alias, target in REGIONAL_ALIASES.items() if target == base]


def _extract_accept_language(request: Any) -> str:
    """Pull the Accept-Language string from a variety of request shapes."""
    if request is None:
        return ""
    if isinstance(request, str):
        return request
    if isinstance(request, dict):
        for key in ("Accept-Language", "accept-language", "ACCEPT_LANGUAGE", "HTTP_ACCEPT_LANGUAGE"):
            if key in request:
                return str(request[key] or "")
        return ""
    # Flask / Werkzeug-style request
    headers = getattr(request, "headers", None)
    if headers is not None:
        try:
            value = headers.get("Accept-Language", "")
        except (AttributeError, TypeError):
            value = ""
        if value:
            return str(value)
    return ""
