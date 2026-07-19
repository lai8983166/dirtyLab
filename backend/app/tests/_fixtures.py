"""Shared binary fixtures for tests."""
from __future__ import annotations

from PIL import Image
import io


def make_png(color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    """Return a real, parseable PNG. Generated at import time so all tests use
    a single source of truth."""
    img = Image.new("RGB", (1, 1), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# A 1x1 red PNG (69 bytes) used as original image + sync content in tests.
PNG_1x1_RED = make_png((255, 0, 0))
