from __future__ import annotations

from pathlib import Path

import boto3

from categoryrag.config import AWS_REGION, S3_BUCKET


class S3Storage:
    def __init__(self) -> None:
        if not S3_BUCKET:
            raise RuntimeError("S3_BUCKET is not set")
        self._bucket = S3_BUCKET
        self._client = boto3.client("s3", region_name=AWS_REGION or None)

    @staticmethod
    def object_key(category_id: str, document_id: str, filename: str) -> str:
        return f"categories/{category_id}/{document_id}/{filename}"

    @staticmethod
    def category_prefix(category_id: str) -> str:
        return f"categories/{category_id}/"

    def upload_file(self, local_path: Path, key: str) -> str:
        self._client.upload_file(str(local_path), self._bucket, key)
        return key

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def delete_prefix(self, prefix: str) -> None:
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            objects = page.get("Contents") or []
            if not objects:
                continue
            self._client.delete_objects(
                Bucket=self._bucket,
                Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
            )


_s3_storage: S3Storage | None = None


def get_s3_storage() -> S3Storage:
    global _s3_storage
    if _s3_storage is None:
        _s3_storage = S3Storage()
    return _s3_storage
