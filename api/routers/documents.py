import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, status

from api.config import settings
from api.database import GetDB
from api.models.document import Document
from api.schemas.document import DocumentResponse

router = APIRouter(tags=["Documents"])
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024
UPLOADS_DIR = Path(settings.UPLOADS_DIR)

UPLOADS_DIR.mkdir(exist_ok=True, parents=True)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, db: GetDB) -> DocumentResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type ({file.content_type}) not allowed. Only support PDF files.",
        )
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    file_id = uuid4()

    file_path = Path(UPLOADS_DIR) / (str(file_id) + os.path.splitext(file.filename)[1])

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save file: {e}"
        ) from e

    doc = Document(
        id=file_id,
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(content),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return DocumentResponse.model_validate(doc)
