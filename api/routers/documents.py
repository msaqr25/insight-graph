from pathlib import Path
from typing import Any
from uuid import UUID

from arq.jobs import Job, JobResult, JobStatus
from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from api.config import settings
from api.database import GetDB
from api.schemas.document import (
    DocumentDeleteResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentResponse,
)
from api.services.document_service import document_service
from api.services.file_service import file_service

router = APIRouter(tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(req: Request, file: UploadFile, db: GetDB) -> DocumentResponse:
    await file_service.validate(file)

    filename = file.filename or ""
    content_type = file.content_type or "application/pdf"

    content = await file_service.read_with_limit(file)

    file_id, file_path = await file_service.save(content, filename)

    try:
        doc = await document_service.create(
            db=db,
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
        )
    except Exception:
        file_service.cleanup(file_path)
        raise

    await req.app.state.arq_redis.enqueue_job("extract_text", str(file_path), str(doc.id))

    return DocumentResponse.model_validate(doc)


@router.get("/job/{job_id}")
async def get_job_status(req: Request, job_id: str):
    job = Job(job_id, req.app.state.arq_redis)
    job_status = await job.status()

    if job_status == JobStatus.not_found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    response: dict[str, Any] = {"job_id": job_id, "status": job_status.value}

    if job_status == JobStatus.complete:
        info = await job.info()

        if isinstance(info, JobResult):
            response["result"] = info.result
            response["execution_time_ms"] = (
                (info.finish_time - info.start_time).total_seconds() * 1000
                if info.finish_time and info.start_time
                else None
            )

    return response


@router.get("/documents")
async def list_documents(db: GetDB) -> DocumentListResponse:
    documents = await document_service.get_all(db)

    result = []
    for doc in documents:
        chunk_count = await document_service.get_chunk_count(db, doc.id)
        result.append(
            DocumentListItem(
                id=doc.id,
                filename=doc.filename,
                status=doc.status.value,
                chunk_count=chunk_count,
                created_at=doc.created_at,
            )
        )

    return DocumentListResponse(documents=result, total=len(result))


@router.get("/documents/{document_id}")
async def get_document(req: Request, document_id: str, db: GetDB) -> FileResponse:
    from uuid import UUID

    doc_id = UUID(document_id)
    document = await document_service.get(db, doc_id)

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = Path(settings.UPLOADS_DIR) / f"{doc_id}.pdf"

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=document.filename,
        media_type=document.content_type,
    )


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(document_id: str, db: GetDB) -> DocumentDeleteResponse:
    doc_id = UUID(document_id)
    deleted = await document_service.delete(db, doc_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DocumentDeleteResponse(id=doc_id, deleted=True)
