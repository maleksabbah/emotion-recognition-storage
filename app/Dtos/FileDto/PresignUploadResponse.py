from __future__ import annotations

from pydantic import BaseModel


class PresignUploadResponse(BaseModel):
    file_id: str
    upload_url: str
    s3_key: str