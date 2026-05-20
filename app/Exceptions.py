"""
Domain exceptions + central FastAPI handler for the storage service.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("storage.exceptions")


class DomainException(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail: str = "Internal server error"

    def __init__(self, detail: Optional[str] = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


# 4xx --------------------------------------------------------------------

class BadRequest(DomainException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Bad request"


class NotFound(DomainException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Not found"


class FileNotFound(NotFound):
    default_detail = "File not found"


# 5xx --------------------------------------------------------------------

class S3Error(DomainException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Object storage error"


class PresignFailed(S3Error):
    default_detail = "Failed to presign URL"


class UploadFailed(S3Error):
    default_detail = "Failed to upload to object storage"


# Handler ----------------------------------------------------------------

async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error(
            "Domain 5xx on %s %s: %s",
            request.method, request.url.path, exc.detail,
        )
    else:
        logger.info(
            "Domain %s on %s %s: %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainException, domain_exception_handler)