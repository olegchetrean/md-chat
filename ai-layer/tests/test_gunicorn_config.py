"""Tests for ``gunicorn.conf.py``.

The config is a plain python module gunicorn imports at startup; we import it
the same way and assert it exposes the expected variables and hooks with
sensible defaults. We re-import the module under various env vars to verify
the env knobs work.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Resolve gunicorn.conf.py once — sits in the ai-layer/ root, two levels up
# from this file (tests/test_gunicorn_config.py).
CONF_PATH = Path(__file__).resolve().parent.parent / "gunicorn.conf.py"


def _load_conf(env: dict[str, str] | None = None, module_name: str = "gunicorn_conf_under_test") -> Any:
    """Import gunicorn.conf.py fresh, optionally overriding env vars."""
    # Save and patch env so each test gets a clean view.
    saved: dict[str, str | None] = {}
    if env:
        for key, val in env.items():
            saved[key] = os.environ.get(key)
            os.environ[key] = val
    try:
        # Drop any cached copy first so module-level code re-runs.
        sys.modules.pop(module_name, None)
        spec = importlib.util.spec_from_file_location(module_name, CONF_PATH)
        assert spec is not None and spec.loader is not None, "spec_from_file_location returned None"
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        # Restore env so subsequent tests aren't poisoned.
        if env:
            for key, prior in saved.items():
                if prior is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prior


def test_config_file_exists_at_expected_path() -> None:
    assert CONF_PATH.is_file(), f"missing gunicorn.conf.py at {CONF_PATH}"


def test_config_imports_without_error() -> None:
    """Smoke test — the most common breakage is a syntax/typo error."""
    conf = _load_conf()
    assert conf is not None


def test_required_gunicorn_settings_present() -> None:
    """Verify all settings gunicorn reads are exposed with the right types."""
    conf = _load_conf()
    # Server socket
    assert isinstance(conf.bind, str) and conf.bind.endswith(":5002"), f"unexpected default bind: {conf.bind}"
    assert conf.bind.startswith("0.0.0.0:"), "must bind all interfaces by default"
    assert isinstance(conf.backlog, int) and conf.backlog > 0
    # Workers
    assert isinstance(conf.workers, int) and conf.workers >= 1
    assert conf.workers <= 8, "worker count must be capped at 8 per spec"
    assert conf.worker_class == "gthread"
    assert conf.threads == 4
    # Timeouts
    assert conf.timeout == 30
    assert conf.keepalive == 5
    assert conf.graceful_timeout >= 1
    # Recycling
    assert conf.max_requests == 1000
    assert conf.max_requests_jitter == 50
    # Logging — gunicorn treats "-" as stdout/stderr (Docker-friendly).
    assert conf.accesslog == "-"
    assert conf.errorlog == "-"
    assert conf.proc_name == "md-chat-ai"


def test_worker_count_formula_respects_cpu_and_cap() -> None:
    """Re-run the worker formula via the helper to confirm the 2*CPU+1, cap-8 rule."""
    conf = _load_conf()
    cpu = os.cpu_count() or 1
    expected = min(2 * cpu + 1, 8)
    # When AI_LAYER_WORKERS is unset, _compute_worker_count() must follow the formula.
    assert conf._compute_worker_count() == expected


def test_worker_count_can_be_overridden_via_env() -> None:
    conf = _load_conf(env={"AI_LAYER_WORKERS": "3"}, module_name="gunicorn_conf_override")
    assert conf.workers == 3


def test_loglevel_respects_env_var() -> None:
    conf = _load_conf(env={"LOG_LEVEL": "DEBUG"}, module_name="gunicorn_conf_loglevel")
    assert conf.loglevel == "debug", "gunicorn expects lowercase loglevel"


def test_hooks_are_callable_and_safe(caplog: pytest.LogCaptureFixture) -> None:
    """on_starting / post_fork / on_exit must not raise when given doubles."""
    conf = _load_conf()

    class _FakeLog:
        def info(self, *_a: Any, **_kw: Any) -> None: ...
        def warning(self, *_a: Any, **_kw: Any) -> None: ...
        def error(self, *_a: Any, **_kw: Any) -> None: ...

    class _FakeServer:
        log = _FakeLog()

    class _FakeWorker:
        pid = 12345
        age = 1
        log = _FakeLog()

    # Should not raise. If md_chat_ai.wsgi import fails (e.g. in a minimal env)
    # the hook must swallow it via the try/except inside on_starting.
    with caplog.at_level(logging.INFO):
        conf.on_starting(_FakeServer())
        conf.post_fork(_FakeServer(), _FakeWorker())
        conf.worker_int(_FakeWorker())
        conf.worker_abort(_FakeWorker())
        conf.on_exit(_FakeServer())
