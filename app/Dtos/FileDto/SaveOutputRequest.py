from __future__ import annotations

from pydantic import BaseModel


class SaveOutputRequest(BaseModel):
    """
    POST /internal/save-output — burner hands base64 of the burned output
    file, storage uploads + records.
    """
    session_id: str
    data: str            # base64 bytes of the output file
    mime_type: str
    file_type: str = "burned"