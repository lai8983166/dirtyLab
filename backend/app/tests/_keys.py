"""Helpers to generate OpenSSH ed25519 private keys for tests.

paramiko 5.0 removed the convenience ``Ed25519Key.generate()`` classmethod, so
we generate the keypair with ``cryptography`` and serialize it in OpenSSH form.
"""
from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate_ed25519_openssh_text() -> str:
    """Return a freshly generated ed25519 private key in OpenSSH text form."""
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")
