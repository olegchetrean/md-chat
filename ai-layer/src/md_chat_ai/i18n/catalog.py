"""In-memory translation catalog.

Loads flat-dict JSON translation files from the sibling ``translations/``
directory at module import time. Catalog can be reloaded via :func:`reload`
so tests that mutate the JSON files on disk see fresh content without
restarting the interpreter.

Design constraints
------------------
* Single source of truth for the supported language codes.
* No third-party gettext / ICU dependency — this is Sprint 0 plumbing.
* Pure stdlib so it works in CI without extra installs.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Languages we ship translations for. Ordered by Moldova-baseline preference:
# Romanian (state language) > Russian (largest minority) > English (lingua
# franca + fallback) > Ukrainian (diaspora + 2022 refugee influx).
SUPPORTED_LANGUAGES: tuple[str, ...] = ("ro", "ru", "en", "uk")

# Regional code -> base language. RFC 4647 wildcard matching narrows
# `ro-MD` to `ro`, `ru-RU` to `ru`, etc.
REGIONAL_ALIASES: dict[str, str] = {
    "ro-md": "ro",
    "ro-ro": "ro",
    "ru-ru": "ru",
    "ru-md": "ru",
    "ru-ua": "ru",
    "en-us": "en",
    "en-gb": "en",
    "uk-ua": "uk",
}

# Final fallback when the negotiated language has no entry for a key.
FALLBACK_LANGUAGE: str = "en"

_TRANSLATIONS_DIR = Path(__file__).parent / "translations"
_lock = threading.Lock()
_catalog: dict[str, dict[str, str]] = {}


def _load_language(lang: str) -> dict[str, str]:
    """Load a single language file from disk.

    Returns an empty dict (and logs a warning) if the file does not exist
    or is malformed — never raises, because i18n must not crash the API.
    """
    path = _TRANSLATIONS_DIR / f"{lang}.json"
    if not path.exists():
        logger.warning("i18n: translations file missing for %s at %s", lang, path)
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("i18n: failed to load %s: %s", path, exc)
        return {}

    if not isinstance(data, dict):
        logger.error("i18n: %s is not a JSON object — got %s", path, type(data).__name__)
        return {}
    # Coerce values to str; reject non-string entries with a warning.
    cleaned: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = value
        else:
            logger.warning("i18n: %s key %r has non-string value, skipped", path, key)
    return cleaned


def load_all() -> None:
    """Populate the in-memory catalog for every supported language."""
    with _lock:
        _catalog.clear()
        for lang in SUPPORTED_LANGUAGES:
            _catalog[lang] = _load_language(lang)


def reload() -> None:
    """Re-read every translation file. Useful for tests that mutate JSON."""
    load_all()


def get_catalog() -> dict[str, dict[str, str]]:
    """Return the loaded catalog (mutating the dict is undefined behavior)."""
    if not _catalog:
        load_all()
    return _catalog


def available_languages() -> tuple[str, ...]:
    """Return the tuple of supported base language codes."""
    return SUPPORTED_LANGUAGES


def normalize_language(code: str | None) -> str:
    """Map a raw locale code (``ro-MD``, ``RU_ru``, ``en``) to a base code.

    Falls back to :data:`FALLBACK_LANGUAGE` for unknown / empty inputs.
    """
    if not code:
        return FALLBACK_LANGUAGE
    candidate = code.strip().lower().replace("_", "-")
    if candidate in SUPPORTED_LANGUAGES:
        return candidate
    if candidate in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[candidate]
    base = candidate.split("-", 1)[0]
    if base in SUPPORTED_LANGUAGES:
        return base
    return FALLBACK_LANGUAGE


# Prime the catalog at import time so the first translate() call is fast.
load_all()
