from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SourceObjectResponse(BaseModel):
    """GET /internal/sessions/{id}/source — the uploaded source, as S3 sees it."""
    file_id: str
    s3_key: str
    size_bytes: int              # ContentLength from HEAD (actual, not declared)
    mime_type: Optional[str] = None
