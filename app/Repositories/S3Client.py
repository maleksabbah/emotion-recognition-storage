"""
S3Client — boto3 wrapper for MinIO.

Wraps both ops_client (internal endpoint, for PUT/GET) and presign_client
(public endpoint, for URLs the browser will hit). Services receive both
via constructor.

boto3 is synchronous — we run blocking calls in a thread via asyncio.to_thread
so the FastAPI event loop stays free.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.Config import (
    PRESIGN_DOWNLOAD_TTL_SECONDS,
    PRESIGN_UPLOAD_TTL_SECONDS,
    S3_BUCKET,
)
from app.Exceptions import PresignFailed, UploadFailed

logger = logging.getLogger("storage.s3-client")


class S3Client:
    def __init__(self, ops_client: Any, presign_client: Any, bucket: str = S3_BUCKET):
        self.ops = ops_client
        self.presign = presign_client
        self.bucket = bucket

    # ── Presigning ──────────────────────────────────

    async def presign_put(self, s3_key: str, content_type: str) -> str:
        def _go() -> str:
            return self.presign.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=PRESIGN_UPLOAD_TTL_SECONDS,
            )
        try:
            return await asyncio.to_thread(_go)
        except Exception as e:
            logger.error("presign_put failed for %s: %s", s3_key, e)
            raise PresignFailed()

    async def presign_get(self, s3_key: str) -> str:
        def _go() -> str:
            return self.presign.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=PRESIGN_DOWNLOAD_TTL_SECONDS,
            )
        try:
            return await asyncio.to_thread(_go)
        except Exception as e:
            logger.error("presign_get failed for %s: %s", s3_key, e)
            raise PresignFailed()

    # ── Direct upload (server-side, for crops / burned output) ──────

    async def put_object(
        self, s3_key: str, body: bytes, content_type: str
    ) -> None:
        def _go() -> None:
            self.ops.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=body,
                ContentType=content_type,
            )
        try:
            await asyncio.to_thread(_go)
        except Exception as e:
            logger.error("put_object failed for %s: %s", s3_key, e)
            raise UploadFailed()

    # ── Probe ───────────────────────────────────────

    async def head_object(self, s3_key: str) -> dict[str, Any]:
        def _go() -> dict[str, Any]:
            return self.ops.head_object(Bucket=self.bucket, Key=s3_key)
        return await asyncio.to_thread(_go)