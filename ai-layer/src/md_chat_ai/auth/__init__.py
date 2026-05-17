"""Authentication module for MD-Chat AI layer.

Provides phone+SMS verification (Infobip), TOTP MFA (RFC 6238), and
PIN-derived key wrapping (Signal SVR3-pattern stub).

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

from . import phone_verification, pin_backup, totp_mfa

__all__ = ["phone_verification", "totp_mfa", "pin_backup"]
