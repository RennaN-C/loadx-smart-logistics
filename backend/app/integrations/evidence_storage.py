"""Private opaque storage port and development-only adapters; no public URLs."""

import os
import uuid
from pathlib import Path
from threading import RLock
from typing import Protocol

MAX_STORED_BYTES = 5 * 1024 * 1024


class EvidenceStorageError(Exception):
    def __init__(self) -> None:
        super().__init__("evidence storage unavailable")


class EvidenceStorage(Protocol):
    def put(self, key: uuid.UUID, content: bytes) -> None:
        """Create an immutable object. On failure caller may discard only this key."""

    def read(self, key: uuid.UUID) -> bytes:
        """Read a private object; never return a public/provider URL."""

    def discard(self, key: uuid.UUID) -> None:
        """Idempotent compensation for an uncommitted newly-created object only."""


class FakeEvidenceStorage:
    def __init__(self) -> None:
        self.objects: dict[uuid.UUID, bytes] = {}
        self._lock = RLock()

    def put(self, key: uuid.UUID, content: bytes) -> None:
        with self._lock:
            if key in self.objects:
                raise EvidenceStorageError
            self.objects[key] = content

    def read(self, key: uuid.UUID) -> bytes:
        with self._lock:
            if key not in self.objects:
                raise EvidenceStorageError
            return self.objects[key]

    def discard(self, key: uuid.UUID) -> None:
        with self._lock:
            self.objects.pop(key, None)


class LocalEvidenceStorage:
    def __init__(self, root: Path) -> None:
        try:
            if root.is_symlink():
                raise EvidenceStorageError
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            if root.stat().st_mode & 0o077:
                raise EvidenceStorageError
            self.root = root.resolve(strict=True)
        except OSError:
            raise EvidenceStorageError from None

    def _path(self, key: uuid.UUID) -> Path:
        if not isinstance(key, uuid.UUID):
            raise EvidenceStorageError
        return self.root / f"{key.hex}.bin"

    def put(self, key: uuid.UUID, content: bytes) -> None:
        try:
            descriptor = os.open(
                self._path(key),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            raise EvidenceStorageError from None

    def read(self, key: uuid.UUID) -> bytes:
        try:
            descriptor = os.open(self._path(key), os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                data = stream.read(MAX_STORED_BYTES + 1)
            if len(data) > MAX_STORED_BYTES:
                raise EvidenceStorageError
            return data
        except OSError:
            raise EvidenceStorageError from None

    def discard(self, key: uuid.UUID) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError:
            raise EvidenceStorageError from None
