"""In-process SFTP test double.

Sync walks the remote workspace in two passes: first ``listdir(workspace)``
to discover top-level subdirectories (``input/``, ``output/``, etc.), then
``listdir(<workspace>/<subdir>)`` to enumerate files. Our fake therefore needs
to understand directory hierarchy, not just flat filename lookups.

We accept a flat ``{absolute_path: bytes}`` mapping at construction time and
derive the directory structure from the path components.
"""
from __future__ import annotations

import io
import os
import time
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass
class FakeEntry:
    """Mimics paramiko's SFTPAttributes - exposes ``st_size`` and ``st_mtime``
    plus a ``filename`` so sync code can treat it like a real result."""
    filename: str
    st_size: int
    st_mtime: float


class FakeSFTP:
    """Tree derived from ``{absolute_path: bytes}``.

    ``listdir_attr(path)`` returns synthetic entries for every direct child of
    ``path`` (whether directory or file). ``stat(path)`` and ``getfo`` work on
    files only.
    """

    def __init__(self, files: dict[str, bytes]) -> None:
        # files: {absolute_path: bytes}
        self.files = dict(files)
        self._dirs: dict[str, set[str]] = {}
        for path in self.files:
            parent = str(PurePosixPath(path).parent)
            name = PurePosixPath(path).name
            self._dirs.setdefault(parent, set()).add(name)
            # Register every intermediate directory.
            cur = PurePosixPath(path)
            while cur.parent != cur:
                cur = cur.parent
                grand = str(cur.parent)
                if cur.name:
                    self._dirs.setdefault(grand, set()).add(cur.name)

    def listdir_attr(self, path: str) -> list[FakeEntry]:
        children = self._dirs.get(path)
        if children is None:
            raise FileNotFoundError(path)
        out: list[FakeEntry] = []
        for name in sorted(children):
            full = f"{path.rstrip('/')}/{name}"
            if full in self.files:
                size = len(self.files[full])
            else:
                size = 0  # directory
            out.append(FakeEntry(filename=name, st_size=size, st_mtime=time.time()))
        return out

    def stat(self, path: str):
        if path not in self.files:
            raise FileNotFoundError(path)
        return _Stat(st_size=len(self.files[path]), st_mtime=time.time())

    def getfo(self, path: str, stream) -> None:
        if path not in self.files:
            raise FileNotFoundError(path)
        stream.write(self.files[path])

    def close(self) -> None:
        pass


@dataclass
class _Stat:
    st_size: int
    st_mtime: float

    # Backward-compat aliases.
    @property
    def size(self) -> int:
        return self.st_size

    @property
    def mtime(self) -> float:
        return self.st_mtime


class FakeSSHClient:
    def __init__(self, sftp: FakeSFTP) -> None:
        self._sftp = sftp

    def open_sftp(self) -> FakeSFTP:
        return self._sftp

    def close(self) -> None:
        pass


def install_fake_sftp(monkeypatch, files: dict[str, bytes]) -> FakeSSHClient:
    """Patch the sync module's SSH client factory to return our fake."""
    from app.services import sync as sync_mod

    client = FakeSSHClient(FakeSFTP(files))

    def fake_ssh_client(_cfg, _conn):
        return client

    monkeypatch.setattr(sync_mod, "_ssh_client", fake_ssh_client)
    return client
