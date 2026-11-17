from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator

_ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo",
    "audio/mpeg", "audio/wav", "audio/webm",
})


class PresignUploadRequest(BaseModel):
    """POST /internal/presign/upload."""
    session_id: str
    file_type: str          # 'video', 'image', etc.
    mime_type: str
    original_filename: Optional[str] = None
    user_id: Optional[str] = None

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        if v not in _ALLOWED_MIME_TYPES:
            raise ValueError(f"mime_type '{v}' is not allowed")
        return v