"""Smoke tests for the WSGI entry point.

CONFIG is a frozen dataclass — we patch attributes via ``unittest.mock.patch.object``
with ``new_callable=property`` or by replacing CONFIG itself with a dataclass replace.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from md_chat_ai import wsgi


def test_configure_logging_runs_without_raising():
    """basicConfig should be callable without crashing; no assertions on side-effects."""
    wsgi._configure_logging()


def test_main_in_dev_mode_calls_app_run_with_debug_true():
    fake_app = MagicMock()
    dev_cfg = replace(wsgi.CONFIG, dev_mode=True, port=5099)
    with (
        patch.object(wsgi, "create_app", return_value=fake_app),
        patch.object(wsgi, "CONFIG", dev_cfg),
        patch.dict("os.environ", {"HOST": "127.0.0.1"}, clear=False),
    ):
        wsgi.main()

    fake_app.run.assert_called_once()
    _, kwargs = fake_app.run.call_args
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 5099
    assert kwargs["debug"] is True


def test_main_in_prod_mode_disables_debug():
    fake_app = MagicMock()
    prod_cfg = replace(wsgi.CONFIG, dev_mode=False, port=5099)
    import os

    if "HOST" in os.environ:
        del os.environ["HOST"]

    with (
        patch.object(wsgi, "create_app", return_value=fake_app),
        patch.object(wsgi, "CONFIG", prod_cfg),
    ):
        wsgi.main()

    fake_app.run.assert_called_once()
    _, kwargs = fake_app.run.call_args
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["debug"] is False


def test_wsgi_module_is_importable_standalone():
    import md_chat_ai.wsgi as w

    assert callable(w.main)
    assert callable(w._configure_logging)


def test_main_invokes_create_app_once():
    fake_app = MagicMock()
    dev_cfg = replace(wsgi.CONFIG, dev_mode=True)
    with (
        patch.object(wsgi, "create_app", return_value=fake_app) as mock_create,
        patch.object(wsgi, "CONFIG", dev_cfg),
    ):
        wsgi.main()

    assert mock_create.call_count == 1


def test_wsgi_module_exposes_create_app_reference():
    assert wsgi.create_app is not None
