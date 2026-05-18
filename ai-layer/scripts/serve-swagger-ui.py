#!/usr/bin/env python3
"""Local Swagger UI server for ``ai-layer/openapi.yaml``.

Runs a tiny Flask app on http://localhost:5050 that serves:

* ``/``               — Swagger UI shell (loaded from the unpkg CDN).
* ``/openapi.yaml``   — the hand-written spec, sent with the right
  ``Content-Type`` so Swagger UI can render it.
* ``/openapi.json``   — JSON view of the same spec, for tooling.

We deliberately use the CDN-hosted Swagger UI rather than vendoring
the assets so the dev-only dependency surface stays minimal. The CDN
is opt-in (this script never runs in prod).

Run:

.. code-block:: bash

    python scripts/serve-swagger-ui.py

License: Apache-2.0.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml
from flask import Flask, Response, jsonify, render_template_string, send_file

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_YAML = ROOT / "openapi.yaml"

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>MD-Chat AI Layer — Swagger UI</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css" />
  <style>
    body { margin: 0; background: #fafafa; }
    .topbar { display: none; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function () {
      window.ui = SwaggerUIBundle({
        url: "/openapi.yaml",
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        layout: "StandaloneLayout",
        tryItOutEnabled: true,
        persistAuthorization: true,
      });
    };
  </script>
</body>
</html>
"""


def _load_spec() -> dict:
    if not OPENAPI_YAML.exists():
        print(f"error: {OPENAPI_YAML} does not exist", file=sys.stderr)
        sys.exit(2)
    with OPENAPI_YAML.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return render_template_string(INDEX_HTML)

    @app.get("/openapi.yaml")
    def openapi_yaml():
        return send_file(
            OPENAPI_YAML,
            mimetype="application/yaml",
            as_attachment=False,
            download_name="openapi.yaml",
        )

    @app.get("/openapi.json")
    def openapi_json():
        return jsonify(_load_spec())

    @app.get("/healthz")
    def healthz() -> Response:
        return Response("ok", mimetype="text/plain")

    return app


def main() -> None:
    host = os.getenv("SWAGGER_HOST", "127.0.0.1")
    port = int(os.getenv("SWAGGER_PORT", "5050"))
    # Sanity check: parse the YAML now so we fail fast.
    _ = _load_spec()
    app = create_app()
    print(f"Swagger UI on http://{host}:{port}")
    print(f"Spec: {OPENAPI_YAML}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
