#!/usr/bin/env python3
"""One-shot generator for an Ed25519 audit-log signing key.

Writes the private key as PKCS#8 PEM with ``0600`` filesystem permissions and
prints the corresponding public JWK to stdout so the operator can paste it
into the ``/.well-known/jwks-audit.json`` document or hand it to a court /
auditor.

Usage:
    python scripts/generate-audit-key.py /etc/md-chat/audit/audit-1.pem
    python scripts/generate-audit-key.py /tmp/test-audit-key.pem --kid mpass-audit-1

Exit codes:
    0  — key generated successfully
    1  — target already exists (use --force to overwrite)
    2  — filesystem / permission error

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

# Make ``src`` importable when running from a fresh clone.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from md_chat_ai.eevidence.keys import (  # noqa: E402  (post-sys.path tweak)
    generate_keypair,
    public_jwk,
    serialize_public_key,
    write_private_key,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an Ed25519 audit-log signing key for MD-Chat eEvidence.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Destination path for the PEM-encoded private key (created with 0600).",
    )
    parser.add_argument(
        "--kid",
        default="mpass-audit-1",
        help="Key identifier embedded in the JWS header (default: mpass-audit-1).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing file at <path>.",
    )
    parser.add_argument(
        "--print-pem",
        action="store_true",
        help="Also print the public-key PEM to stdout (after the JWK JSON).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    target: Path = args.path

    if target.exists() and not args.force:
        print(
            f"refusing to overwrite existing key at {target} — pass --force to override",
            file=sys.stderr,
        )
        return 1

    if target.exists() and args.force:
        try:
            target.unlink()
        except OSError as exc:
            print(f"could not remove existing key {target}: {exc}", file=sys.stderr)
            return 2

    try:
        key = generate_keypair()
        written = write_private_key(target, key)
    except OSError as exc:
        print(f"failed to write key to {target}: {exc}", file=sys.stderr)
        return 2

    # Sanity-check the permission bits — the production deployment depends on
    # this being exactly 0600 for the load_private_key() guard to accept it.
    mode = stat.S_IMODE(os.stat(written).st_mode)
    if mode != 0o600:
        # Last-ditch attempt to fix permissions.
        try:
            os.chmod(written, 0o600)
            mode = stat.S_IMODE(os.stat(written).st_mode)
        except OSError:
            pass
    if mode != 0o600:
        print(
            f"warning: key written but permissions are {oct(mode)} instead of 0o600. "
            f"Run: chmod 0600 {written}",
            file=sys.stderr,
        )

    public_key = key.public_key()
    jwk = public_jwk(public_key, kid=args.kid)

    print(f"private key written: {written}  (mode={oct(mode)})", file=sys.stderr)
    print(f"kid:                  {args.kid}", file=sys.stderr)
    print(file=sys.stderr)
    print(json.dumps(jwk, indent=2, sort_keys=True))

    if args.print_pem:
        print(serialize_public_key(public_key).decode("utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
