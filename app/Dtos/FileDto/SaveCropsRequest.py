from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

_ALLOWED_REGIONS = frozenset({"face", "eyes", "mouth", "cheeks", "forehead"})
_MAX_BASE64_LEN = 1_400_000


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

    @field_validator("crops")
    @classmethod
    def validate_crops(cls, v: dict[str, str]) -> dict[str, str]:
        for region, b64 in v.items():
            if region not in _ALLOWED_REGIONS:
                raise ValueError(f"region '{region}' not in {sorted(_ALLOWED_REGIONS)}")
            if len(b64) > _MAX_BASE64_LEN:
                raise ValueError(
                    f"base64 for region '{region}' exceeds {_MAX_BASE64_LEN} chars"
                )
        return v