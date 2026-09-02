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

    @abstractmethod
    def delete(self, path: str) -> None:
        """Remove a stored object. Must not raise if it is already gone."""


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

    def delete(self, path: str) -> None:
        (self.base_dir / path).unlink(missing_ok=True)


class S3FileStorage(FileStorage):
    """S3 / MinIO backed storage.

    Durable and shared across every API replica (local disk is neither). A
    fuller implementation would hand the browser a presigned URL so the file
    bytes never transit the API at all.
    """

    def __init__(self) -> None:
        import boto3  # imported lazily so the local backend needs no boto3

        self._boto3 = boto3
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                # Bucket may already exist / be managed externally.
                pass

    def save(self, data: bytes, filename: str) -> str:
        from pathlib import Path as _Path

        key = f"{uuid.uuid4().hex}{_Path(filename).suffix}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def read(self, path: str) -> bytes:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=path)
            return resp["Body"].read()
        except self.client.exceptions.NoSuchKey as exc:
            raise FileNotFoundError(path) from exc

    def delete(self, path: str) -> None:
        # delete_object is idempotent — no error if the key is already gone.
        self.client.delete_object(Bucket=self.bucket, Key=path)


def get_storage() -> FileStorage:
    if settings.storage_backend.lower() == "s3":
        return S3FileStorage()
    return LocalFileStorage(os.path.abspath(settings.upload_dir))
