"""SSH key validation utilities.

The spec scenario "Detect an unavailable instance" requires that we report a
diagnosable failure for the missing-key case. ``validate_private_key`` checks
that the local key material is parseable and warn the user about world-readable
permissions before we attempt to connect.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import paramiko


@dataclass
class KeyValidation:
    ok: bool
    detail: str
    key_type: str | None = None
    fingerprint: str | None = None
    permission_warning: str | None = None


def validate_private_key(key_text: str, *, file_path: Path | None = None) -> KeyValidation:
    if not key_text or not key_text.strip():
        return KeyValidation(ok=False, detail="Private key is empty.")
    pkey: paramiko.PKey | None = None
    errors: list[str] = []
    loaders = [paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey]
    if hasattr(paramiko, "DSSKey"):  # removed in paramiko 5+
        loaders.append(getattr(paramiko, "DSSKey"))
    for loader in loaders:
        try:
            pkey = loader.from_private_key(io.StringIO(key_text))  # type: ignore[attr-defined]
            break
        except (paramiko.SSHException, EOFError, ValueError) as exc:
            errors.append(str(exc))
    if pkey is None:
        return KeyValidation(
            ok=False,
            detail="The provided private key could not be parsed. Use an OpenSSH-format Ed25519, ECDSA, or RSA key. "
            + (" ".join(errors) if errors else ""),
        )
    warning = None
    if file_path is not None and file_path.exists():
        mode = file_path.stat().st_mode & 0o777
        if mode & 0o077:
            warning = (
                f"Private key file has mode {oct(mode)}. SSH may refuse to use it; "
                "chmod 600 is recommended."
            )
    return KeyValidation(
        ok=True,
        detail="Key parses successfully.",
        key_type=pkey.get_name(),
        fingerprint=hex(pkey.get_bits()) if hasattr(pkey, "get_bits") else None,
        permission_warning=warning,
    )
