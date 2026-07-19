#!/usr/bin/env python3
"""Preflight check for secret/sync exclusion (Task 7.4).

Runs as part of CI or `make check`. Verifies that:
- ``data/`` is in ``.gitignore``.
- ``.env`` is in ``.gitignore``.
- ``secrets/`` and ``*.key`` are in ``.gitignore``.
- The sync allowlist does NOT include any directory called ``secrets`` or
  ``config``.

Doesn't run the full test suite (``make test`` does that). Just a guard.
"""
from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_GITIGNORE_PATTERNS = [
    "data/",
    ".env",
    "secrets/",
    "*.key",
    "*.pem",
    "*.sqlite",
]


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    failures: list[str] = []

    gitignore = repo / ".gitignore"
    if not gitignore.exists():
        failures.append(".gitignore is missing")
    else:
        text = gitignore.read_text(encoding="utf-8")
        for pat in REQUIRED_GITIGNORE_PATTERNS:
            if pat not in text:
                failures.append(f".gitignore missing pattern: {pat}")

    # Sync allowlist guard. Parse the source so this works without backend
    # dependencies installed.
    sync_path = repo / "backend" / "app" / "services" / "sync.py"
    if not sync_path.exists():
        failures.append("backend/app/services/sync.py not found")
    else:
        import ast

        tree = ast.parse(sync_path.read_text(encoding="utf-8"))
        allowlist_keys: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "ALLOWED_KINDS_BY_DIR":
                        if isinstance(node.value, ast.Dict):
                            for k in node.value.keys:
                                if isinstance(k, ast.Constant):
                                    allowlist_keys.add(str(k.value))
        bad = allowlist_keys & {"secrets", "config", ".ssh", ".config"}
        if bad:
            failures.append(f"Sync allowlist includes forbidden dirs: {bad}")

    if failures:
        print("Preflight FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("Preflight OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
