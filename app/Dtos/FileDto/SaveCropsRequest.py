from __future__ import annotations

from pydantic import BaseModel, Field


class SaveCropsRequest(BaseModel):
    """
    POST /internal/save-crops — orchestrator hands base64 JPEG crops, storage
    decodes + uploads + records each row.

    `crops` is a mapping region → base64 bytes:
        {"face": "...", "eyes": "...", "mouth": "...",
         "cheeks": "...", "forehead": "..."}
    """
    session_id: str
    frame_index: int
    detection_index: int
    crops: dict[str, str] = Field(default_factory=dict)