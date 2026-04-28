from typing import Any

from arq.jobs import Job, JobResult, JobStatus
from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from api.database import GetDB
from api.schemas.document import DocumentResponse
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
