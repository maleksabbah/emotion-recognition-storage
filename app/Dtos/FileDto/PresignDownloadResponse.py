from __future__ import annotations

from pydantic import BaseModel


class PresignDownloadResponse(BaseModel):
    file_id: str
    download_url: str
    file_type: str
    s3_key: str