import os
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, status

from api.config import settings
from api.database import GetDB
from api.models.document import Document
from api.schemas.document import DocumentResponse

router = APIRouter(tags=["Documents"])


def get_uploads_dir() -> Path:
    uploads_dir = Path(settings.UPLOADS_DIR)
    uploads_dir.mkdir(exist_ok=True, parents=True)
    return uploads_dir


async def read_file_with_limit(file: UploadFile, max_size: int) -> bytes:
    content = b""
    while chunk := await file.read(8192):
        if len(content) + len(chunk) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {max_size // (1024 * 1024)}MB",
            )
        content += chunk
    return content


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, db: GetDB) -> DocumentResponse:
    max_file_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024

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
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext or ext not in (".pdf",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must have a valid PDF extension",
        )

    content = await read_file_with_limit(file, max_file_size)

    file_id = uuid4()
    file_path = get_uploads_dir() / (str(file_id) + ext)
    file_path_str = str(file_path)

    try:
        async with aiofiles.open(file_path_str, "wb") as f:
            await f.write(content)
    except Exception as e:
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file",
        ) from e

    doc = Document(
        id=file_id,
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(content),
    )
    try:
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document metadata",
        ) from e

    return DocumentResponse.model_validate(doc)
