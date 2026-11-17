from __future__ import annotations

from pydantic import BaseModel, Field


class SaveOutputRequest(BaseModel):
    """
    POST /internal/save-output — burner hands base64 of the burned output
    file, storage uploads + records.
    """
    session_id: str
    data: str = Field(max_length=70_000_000)  # base64 bytes of the output file
    mime_type: str
    file_type: str = "burned"