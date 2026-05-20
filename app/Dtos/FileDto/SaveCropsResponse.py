from __future__ import annotations

from pydantic import BaseModel


class SavedCropInfo(BaseModel):
    file_id: str
    s3_key: str


class SaveCropsResponse(BaseModel):
    """Returns one entry per region the orchestrator sent."""
    file_ids: dict[str, SavedCropInfo]