from __future__ import annotations

from pydantic import BaseModel


class DeleteSourceResponse(BaseModel):
    """DELETE /internal/sessions/{id}/source."""
    deleted: int
