from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PresignUploadRequest(BaseModel):
    """POST /internal/presign/upload."""
    session_id: str
    file_type: str          # 'video', 'image', etc.
    mime_type: str
    original_filename: Optional[str] = None
    user_id: Optional[str] = None