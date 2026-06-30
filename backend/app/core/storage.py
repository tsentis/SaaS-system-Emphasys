"""Object storage abstraction.

A small :class:`Storage` protocol decouples the application from S3/MinIO so tests can
substitute an in-memory implementation via the ``get_storage`` dependency.
"""

from functools import lru_cache
from typing import Protocol, runtime_checkable

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


@runtime_checkable
class Storage(Protocol):
    def put_object(self, key: str, data: bytes, content_type: str) -> None: ...
    def get_object(self, key: str) -> bytes: ...
    def delete_object(self, key: str) -> None: ...
    def object_exists(self, key: str) -> bool: ...
    def presigned_get_url(self, key: str, expires: int = 3600) -> str: ...


class S3Storage:
    """S3-compatible storage (AWS S3 in prod, MinIO in dev)."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )
        self._bucket = settings.s3_bucket
        self._ensured = False

    def _ensure_bucket(self) -> None:
        if self._ensured:
            return
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
        self._ensured = True

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )

    def get_object(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def object_exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    def presigned_get_url(self, key: str, expires: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        )


class InMemoryStorage:
    """In-memory storage for tests; mirrors the :class:`Storage` protocol."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = (data, content_type)

    def get_object(self, key: str) -> bytes:
        return self._objects[key][0]

    def delete_object(self, key: str) -> None:
        self._objects.pop(key, None)

    def object_exists(self, key: str) -> bool:
        return key in self._objects

    def presigned_get_url(self, key: str, expires: int = 3600) -> str:
        return f"memory://{key}?expires={expires}"


@lru_cache
def _default_storage() -> S3Storage:
    return S3Storage()


def get_storage() -> Storage:
    """FastAPI dependency returning the configured storage backend."""
    return _default_storage()
