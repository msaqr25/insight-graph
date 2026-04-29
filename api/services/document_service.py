from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.document import Document, DocumentChunk, DocumentStatus


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

    async def get_all(self, db: AsyncSession) -> list[Document]:
        result = await db.execute(select(Document).order_by(Document.created_at.desc()))
        return list(result.scalars().all())

    async def get_chunk_count(self, db: AsyncSession, document_id: UUID) -> int:
        result = await db.execute(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
        )
        return result.scalar() or 0

    async def delete(self, db: AsyncSession, document_id: UUID) -> bool:
        document = await db.get(Document, document_id)
        if not document:
            return False

        await db.delete(document)
        await db.commit()

        file_path = self._get_file_path(document_id)
        if file_path.exists():
            file_path.unlink()

        return True

    def _get_file_path(self, document_id: UUID) -> Path:
        uploads_dir = Path(settings.UPLOADS_DIR)
        return uploads_dir / f"{document_id}.pdf"


document_service = DocumentService()
