from __future__ import annotations

from pydantic import BaseModel


class SaveOutputResponse(BaseModel):
    file_id: str
    s3_key: str