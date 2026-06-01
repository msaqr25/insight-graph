import logging
from uuid import UUID

import pymupdf

from api.graph.neo4j_client import get_neo4j_client
from api.models.document import Document, DocumentChunk, DocumentStatus
from api.schemas.kg import ExtractedEntity, ExtractedRelation
from api.services.kg_extractor import extract_entities_relations
from api.worker.chunker import chunk_text
from api.worker.database import get_session

logger = logging.getLogger(__name__)


async def extract_text(ctx, file_path: str, document_id: str):
    doc_id = UUID(document_id)
    redis = ctx["redis"]

    with get_session() as db:
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        with pymupdf.open(file_path) as pdf_doc:
            text = ""
            for page in pdf_doc:
                text += page.get_text()  # type: ignore[reportOperatorIssue]

        document.status = DocumentStatus.CHUNKING
        db.commit()

    await redis.enqueue_job("chunk_text_task", text, document_id)

    return {"text": text, "document_id": document_id}


async def chunk_text_task(ctx, text: str, document_id: str):
    doc_id = UUID(document_id)
    redis = ctx["redis"]

    with get_session() as db:
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        chunks = chunk_text(text)

        for chunk_data in chunks:
            chunk = DocumentChunk(
                document_id=doc_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
            )
            db.add(chunk)

        db.commit()

        document.status = DocumentStatus.EMBEDDING
        db.commit()

    await redis.enqueue_job("embed_and_store", document_id)
    await redis.enqueue_job("extract_entities_task", document_id)

    return {"chunk_count": len(chunks), "document_id": document_id}


async def embed_and_store(ctx, document_id: str):
    doc_id = UUID(document_id)
    embedding_model = ctx["embedding_model"]

    try:
        with get_session() as db:
            document = db.query(Document).filter(Document.id == doc_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found")

            chunks = (
                db.query(DocumentChunk)
                .filter(
                    DocumentChunk.document_id == doc_id,
                    DocumentChunk.embedding.is_(None),
                )
                .all()
            )

            if not chunks:
                document.status = DocumentStatus.COMPLETED
                db.commit()
                return {"status": "done", "message": "No chunks to embed"}

            contents = [chunk.content for chunk in chunks]
            embeddings = embedding_model.encode(contents, show_progress_bar=True)

            for chunk, embedding in zip(chunks, embeddings, strict=True):
                chunk.embedding = embedding.tolist()

            db.commit()

            document.status = DocumentStatus.COMPLETED
            db.commit()

        return {"status": "done", "embedded_count": len(chunks)}

    except Exception as e:
        logger.error(f"Embedding failed for document {document_id}: {e}")
        with get_session() as db:
            document = db.query(Document).filter(Document.id == doc_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                db.commit()
        raise


async def extract_entities_task(ctx, document_id: str):
    doc_id = UUID(document_id)
    neo4j_client = get_neo4j_client()

    try:
        with get_session() as db:
            document = db.query(Document).filter(Document.id == doc_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found")

            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()

            entity_map: dict[str, ExtractedEntity] = {}
            all_relations: list[ExtractedRelation] = []

            for chunk in chunks:
                try:
                    result = extract_entities_relations(chunk.content)
                except Exception as e:
                    logger.warning(f"Extraction failed for chunk {chunk.id}: {e}")
                    continue

                for entity in result.entities:
                    if entity.name in entity_map:
                        existing = entity_map[entity.name]
                        if len(entity.description) > len(existing.description):
                            entity_map[entity.name] = entity
                    else:
                        entity_map[entity.name] = entity

                all_relations.extend(result.relations)

            unique_entities = list(entity_map.values())

        await neo4j_client.create_entities(unique_entities)
        await neo4j_client.create_relations(all_relations)

        with get_session() as db:
            document = db.query(Document).filter(Document.id == doc_id).first()
            if document and document.status != DocumentStatus.FAILED:
                document.status = DocumentStatus.COMPLETED
                db.commit()

        return {
            "status": "done",
            "entity_count": len(unique_entities),
            "relation_count": len(all_relations),
            "document_id": document_id,
        }

    except Exception as e:
        logger.error(f"Entity extraction failed for document {document_id}: {e}")
        with get_session() as db:
            document = db.query(Document).filter(Document.id == doc_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                db.commit()
        raise
