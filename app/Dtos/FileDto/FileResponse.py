from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    """One row from the files table."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: Optional[str] = None
    category: str
    file_type: str
    s3_key: str
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    original_filename: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None