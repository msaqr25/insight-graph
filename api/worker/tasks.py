from pathlib import Path

import pymupdf

from api.models.document import Document, DocumentChunk, DocumentStatus
from api.worker.chunker import chunk_text
from api.worker.database import SessionLocal


async def extract_text(ctx, file_path: Path | str):
    db = SessionLocal()
    try:
        with pymupdf.open(file_path) as doc:
            text = ""
            for page in doc:
                text += page.get_text()  # type: ignore[reportOperatorIssue]

        parts = str(file_path).split("/")
        doc_id = parts[-1].replace(".pdf", "")
        document = db.query(Document).filter(Document.id == doc_id).first()
        if document:
            document.status = DocumentStatus.CHUNKING
            db.commit()

        return {"status": "done", "text": text, "document_id": doc_id}
    finally:
        db.close()


async def chunk_text_task(ctx, text: str, document_id: str):
    db = SessionLocal()
    try:
        chunks = chunk_text(text)

        for chunk_data in chunks:
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
            )
            db.add(chunk)

        db.commit()

        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.EMBEDDING
            db.commit()

        return {
            "status": "done",
            "chunk_count": len(chunks),
            "document_id": document_id,
        }
    finally:
        db.close()


async def embed_and_store(ctx, document_id: str):
    db = SessionLocal()
    try:
        embedding_model = ctx["embedding_model"]

        chunks = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.embedding.is_(None),
            )
            .all()
        )

        if not chunks:
            return {"status": "done", "message": "No chunks to embed"}

        contents = [chunk.content for chunk in chunks]
        embeddings = embedding_model.encode(contents, show_progress_bar=True)

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding.tolist()

        db.commit()

        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.COMPLETED
            db.commit()

        return {"status": "done", "embedded_count": len(chunks)}
    finally:
        db.close()
