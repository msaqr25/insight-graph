from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: str
    chunk_count: int | None = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class DocumentDeleteResponse(BaseModel):
    id: UUID
    deleted: bool
