"""WSGI entry point — used by Docker and `python -m md_chat_ai.wsgi`."""

from __future__ import annotations

import logging
import os

from .api import create_app
from .config import CONFIG


def _configure_logging() -> None:
    logging.basicConfig(
        level=CONFIG.log_level,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )


def main() -> None:
    _configure_logging()
    app = create_app()
    host = os.getenv("HOST", "0.0.0.0")
    port = CONFIG.port
    if CONFIG.dev_mode:
        app.run(host=host, port=port, debug=True)
    else:
        # In production we expect gunicorn or similar in front.
        # For now, Flask's built-in server suffices for the bootstrap milestone.
        app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
