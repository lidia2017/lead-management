"""File storage abstraction.

The interface makes it a one-class change to swap local disk for S3/GCS in
production. Only metadata + path are kept in the DB; the blob lives here.
"""
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings


class FileStorage(ABC):
    @abstractmethod
    def save(self, data: bytes, filename: str) -> str:
        """Persist ``data`` and return an opaque storage path/key."""

    @abstractmethod
    def read(self, path: str) -> bytes:
        ...


class LocalFileStorage(FileStorage):
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, filename: str) -> str:
        # Prefix with a UUID to avoid collisions; keep the original extension.
        ext = Path(filename).suffix
        key = f"{uuid.uuid4().hex}{ext}"
        dest = self.base_dir / key
        with open(dest, "wb") as fh:
            fh.write(data)
        return str(key)

    def read(self, path: str) -> bytes:
        full = self.base_dir / path
        if not full.exists():
            raise FileNotFoundError(path)
        with open(full, "rb") as fh:
            return fh.read()


def get_storage() -> FileStorage:
    # Extend here for s3/gcs backends keyed off an env var.
    return LocalFileStorage(os.path.abspath(settings.upload_dir))
