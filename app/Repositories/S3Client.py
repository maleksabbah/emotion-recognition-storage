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
from typing import Any, Optional

from botocore.exceptions import ClientError

from app.Config import (
    PRESIGN_DOWNLOAD_TTL_SECONDS,
    PRESIGN_UPLOAD_TTL_SECONDS,
    S3_BUCKET,
)
from app.Exceptions import FileNotFound, PresignFailed, S3Error, UploadFailed

logger = logging.getLogger("storage.s3-client")


class S3Client:
    def __init__(self, ops_client: Any, presign_client: Any, bucket: str = S3_BUCKET):
        self.ops = ops_client
        self.presign = presign_client
        self.bucket = bucket

    # ── Presigning ──────────────────────────────────

    async def presign_put(
        self, s3_key: str, content_type: str, content_length: Optional[int] = None
    ) -> str:
        """
        content_length, when given, becomes a signed header (SigV4 puts it in
        X-Amz-SignedHeaders), so the PUT only verifies with that exact size.
        """
        params: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": s3_key,
            "ContentType": content_type,
        }
        if content_length is not None:
            params["ContentLength"] = content_length

        def _go() -> str:
            return self.presign.generate_presigned_url(
                "put_object",
                Params=params,
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

    async def object_size(self, s3_key: str) -> int:
        """Actual stored size via HEAD. FileNotFound if the object isn't there."""
        try:
            head = await self.head_object(s3_key)
        except ClientError as e:
            code = str(e.response.get("Error", {}).get("Code", ""))
            if code in ("404", "NoSuchKey", "NotFound"):
                raise FileNotFound()
            logger.error("head_object failed for %s: %s", s3_key, e)
            raise S3Error()
        except Exception as e:
            logger.error("head_object failed for %s: %s", s3_key, e)
            raise S3Error()
        return int(head["ContentLength"])

    # ── Delete ──────────────────────────────────────

    async def delete_object(self, s3_key: str) -> None:
        """Idempotent — S3 returns success for a missing key."""
        def _go() -> None:
            self.ops.delete_object(Bucket=self.bucket, Key=s3_key)
        try:
            await asyncio.to_thread(_go)
        except Exception as e:
            logger.error("delete_object failed for %s: %s", s3_key, e)
            raise S3Error()