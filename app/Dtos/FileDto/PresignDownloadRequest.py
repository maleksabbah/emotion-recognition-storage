from __future__ import annotations

from pydantic import BaseModel


class PresignDownloadRequest(BaseModel):
    """POST /internal/presign/download — sign a URL for a known file_id."""
    file_id: str