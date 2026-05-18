"""Tests for the md_chat_ai.i18n package.

Covers:
    * Basic translate() per language (ro, ru, en, uk).
    * Fallback to English on missing key in target language.
    * Fallback to key itself when missing everywhere.
    * Placeholder interpolation (``str.format`` style).
    * Accept-Language negotiation (RFC 4647 lookup).
    * Cyrillic correctness in ru.json (no transliteration).
    * Romanian diacritice (ă â î ș ț) in ro.json.
    * Reload picks up on-disk changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from md_chat_ai import i18n
from md_chat_ai.i18n import (
    available_languages,
    negotiate_language,
    reload,
    translate,
)
from md_chat_ai.i18n.catalog import (
    FALLBACK_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_catalog,
)

TRANSLATIONS_DIR = Path(i18n.__file__).parent / "translations"


# ---------------------------------------------------------------------------
# 1. available_languages
# ---------------------------------------------------------------------------


def test_available_languages_returns_four_codes():
    langs = available_languages()
    assert set(langs) == {"ro", "ru", "en", "uk"}
    assert langs == SUPPORTED_LANGUAGES


# ---------------------------------------------------------------------------
# 2. Basic translate per language
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lang,key,expected_substring",
    [
        ("ro", "welcome.title", "Bine ați venit"),
        ("ru", "welcome.title", "Добро пожаловать"),
        ("en", "welcome.title", "Welcome"),
        ("uk", "welcome.title", "Ласкаво просимо"),
    ],
)
def test_translate_basic_per_language(lang, key, expected_substring):
    assert expected_substring in translate(key, lang)


# ---------------------------------------------------------------------------
# 3. Fallback to English on missing key in target language
# ---------------------------------------------------------------------------


def test_fallback_to_english_when_key_missing_in_target(monkeypatch):
    catalog = get_catalog()
    # Inject an English-only key for the duration of the test.
    monkeypatch.setitem(catalog["en"], "test.fallback_only_en", "English-only fallback string")
    # Ensure other languages do NOT have it.
    for lang in ("ro", "ru", "uk"):
        catalog[lang].pop("test.fallback_only_en", None)

    assert translate("test.fallback_only_en", "ro") == "English-only fallback string"
    assert translate("test.fallback_only_en", "ru") == "English-only fallback string"
    assert translate("test.fallback_only_en", "uk") == "English-only fallback string"


# ---------------------------------------------------------------------------
# 4. Fallback to key on totally missing
# ---------------------------------------------------------------------------


def test_fallback_to_key_when_missing_everywhere(caplog):
    with caplog.at_level("WARNING"):
        result = translate("this.key.absolutely.does.not.exist", "ro")
    assert result == "this.key.absolutely.does.not.exist"
    assert any("missing" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# 5. Placeholder interpolation
# ---------------------------------------------------------------------------


def test_placeholder_interpolation_simple():
    out = translate("auth.phone.code_sent", "en", phone="+37368000000", minutes=5)
    assert "+37368000000" in out
    assert "5" in out


def test_placeholder_interpolation_romanian():
    out = translate("auth.phone.code_sent", "ro", phone="+37368000000", minutes=5)
    assert "+37368000000" in out
    assert "5" in out
    assert "Codul" in out


def test_placeholder_interpolation_missing_kwarg_returns_template(caplog):
    # The template references {phone} and {minutes} but we omit them.
    with caplog.at_level("WARNING"):
        out = translate("auth.phone.code_sent", "en")
    # Should fall back to raw template rather than raising.
    assert "{phone}" in out
    assert "{minutes}" in out


# ---------------------------------------------------------------------------
# 6. Accept-Language negotiation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "header,expected",
    [
        ("ro-MD,ro;q=0.9,en;q=0.7", "ro"),
        ("ru-RU,ru;q=0.9,en;q=0.5", "ru"),
        ("en-US,en;q=0.9", "en"),
        ("uk-UA,uk;q=0.9,ru;q=0.5", "uk"),
        ("fr-FR,fr;q=0.9", "en"),  # unsupported → fallback
        ("", "en"),  # empty → fallback
        ("*", "en"),  # wildcard → fallback
        ("ro", "ro"),
        ("RU", "ru"),  # case-insensitive
    ],
)
def test_negotiate_language(header, expected):
    assert negotiate_language(header) == expected


def test_negotiate_language_respects_q_priority():
    # English is listed first but Romanian has higher q.
    assert negotiate_language("en;q=0.5,ro;q=0.9") == "ro"


def test_negotiate_language_from_dict():
    assert negotiate_language({"Accept-Language": "ru-RU,ru;q=0.9"}) == "ru"
    assert negotiate_language({"accept-language": "uk"}) == "uk"


def test_negotiate_language_from_request_like_object():
    class FakeRequest:
        class _Headers:
            def __init__(self, values):
                self._v = values

            def get(self, key, default=""):
                return self._v.get(key, default)

        def __init__(self, accept):
            self.headers = self._Headers({"Accept-Language": accept})

    assert negotiate_language(FakeRequest("ro-MD,en;q=0.5")) == "ro"


def test_negotiate_language_none_returns_fallback():
    assert negotiate_language(None) == FALLBACK_LANGUAGE


# ---------------------------------------------------------------------------
# 7. Cyrillic correctness — no transliteration in ru.json / uk.json
# ---------------------------------------------------------------------------


def test_russian_uses_native_cyrillic_no_translit():
    text = translate("disclosure.ai_act_art50", "ru")
    # Must contain Cyrillic characters.
    assert any("Ѐ" <= ch <= "ӿ" for ch in text)
    # Must NOT be the latinized config.py fallback ("Vy obshchaetes").
    assert "Vy obshchaetes" not in text
    assert "obshchaetes" not in text


def test_ukrainian_uses_native_cyrillic():
    text = translate("welcome.subtitle", "uk")
    # Ukrainian-specific characters like ї, є, і must appear in at least one uk string.
    full_uk = " ".join(get_catalog()["uk"].values())
    assert any(ch in full_uk for ch in "їєіґ")


# ---------------------------------------------------------------------------
# 8. Romanian diacritice present in ro.json
# ---------------------------------------------------------------------------


def test_romanian_has_diacritics():
    """ro.json must use proper diacritice (ă â î ș ț), not ASCII fallback."""
    full_ro = " ".join(get_catalog()["ro"].values())
    # At least one of each diacritic should appear across the catalog.
    for ch in ("ă", "â", "î", "ș", "ț"):
        assert ch in full_ro, f"Missing diacritic {ch!r} in ro.json — check for ASCII fallback"


# ---------------------------------------------------------------------------
# 9. Reload picks up on-disk changes
# ---------------------------------------------------------------------------


def test_reload_picks_up_disk_changes(tmp_path, monkeypatch):
    # Copy en.json to a tmp path, patch _TRANSLATIONS_DIR, modify, reload.
    from md_chat_ai.i18n import catalog as catalog_module

    original_dir = catalog_module._TRANSLATIONS_DIR

    tmp_translations = tmp_path / "translations"
    tmp_translations.mkdir()
    for lang in SUPPORTED_LANGUAGES:
        src = original_dir / f"{lang}.json"
        (tmp_translations / f"{lang}.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(catalog_module, "_TRANSLATIONS_DIR", tmp_translations)

    # Sanity: existing key still resolves before our mutation.
    reload()
    assert "Welcome" in translate("welcome.title", "en")

    # Mutate the en.json on disk.
    en_path = tmp_translations / "en.json"
    data = json.loads(en_path.read_text(encoding="utf-8"))
    data["welcome.title"] = "MUTATED-WELCOME"
    en_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    reload()
    assert translate("welcome.title", "en") == "MUTATED-WELCOME"

    # Restore for subsequent tests.
    monkeypatch.setattr(catalog_module, "_TRANSLATIONS_DIR", original_dir)
    reload()


# ---------------------------------------------------------------------------
# 10. Catalog completeness — every required key exists in every language.
# ---------------------------------------------------------------------------


REQUIRED_KEYS = {
    "auth.phone.code_sent",
    "auth.phone.code_expired",
    "auth.phone.rate_limit",
    "auth.phone.invalid_format",
    "auth.phone.too_many_attempts",
    "auth.mfa.setup_complete",
    "auth.mfa.invalid_code",
    "auth.mfa.backup_code_used",
    "auth.mfa.required",
    "auth.pin.set",
    "auth.pin.wrong",
    "auth.pin.required_for_recovery",
    "eevidence.submitted",
    "eevidence.received",
    "eevidence.emergency_acknowledged",
    "eevidence.refused",
    "eevidence.responded",
    "identity.evo_verified",
    "identity.mpass_login_redirect",
    "identity.idnp_consent_required",
    "identity.msign_signed",
    "disclosure.ai_act_art50",
    "disclosure.confidential_compute",
    "disclosure.audit_trail",
    "error.invalid_request",
    "error.unauthorized",
    "error.not_found",
    "error.rate_limit",
    "error.server_error",
    "welcome.title",
    "welcome.subtitle",
}


@pytest.mark.parametrize("lang", ["ro", "ru", "en", "uk"])
def test_all_required_keys_present(lang):
    catalog = get_catalog()
    missing = REQUIRED_KEYS - set(catalog[lang])
    assert not missing, f"{lang} catalog is missing required keys: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 11. Regional codes normalize correctly via translate()
# ---------------------------------------------------------------------------


def test_translate_accepts_regional_codes():
    assert translate("welcome.title", "ro-MD") == translate("welcome.title", "ro")
    assert translate("welcome.title", "ru-RU") == translate("welcome.title", "ru")
    assert translate("welcome.title", "en-US") == translate("welcome.title", "en")
    assert translate("welcome.title", "uk-UA") == translate("welcome.title", "uk")


def test_translate_unknown_language_falls_back_to_english():
    assert translate("welcome.title", "klingon") == translate("welcome.title", "en")
