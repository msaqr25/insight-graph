from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.document import Document, DocumentStatus


class DocumentService:
    async def create(
        self,
        db: AsyncSession,
        file_id: UUID,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> Document:
        doc = Document(
            id=file_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            status=DocumentStatus.EXTRACTING,
        )
        try:
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save document metadata",
            ) from e
        return doc

    async def get(self, db: AsyncSession, document_id: UUID) -> Document | None:
        result = await db.get(Document, document_id)
        return result


document_service = DocumentService()
