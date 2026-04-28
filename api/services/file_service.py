import os
from pathlib import Path
from uuid import UUID, uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status

from api.config import settings


class FileService:
    def __init__(self):
        self.uploads_dir = self._get_uploads_dir()

    def _get_uploads_dir(self) -> Path:
        uploads_dir = Path(settings.UPLOADS_DIR)
        uploads_dir.mkdir(exist_ok=True, parents=True)
        return uploads_dir

    async def validate(self, file: UploadFile) -> None:
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type ({file.content_type}) not allowed. Only PDF files are supported.",
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
                detail="Filename must have a .pdf extension",
            )

    async def read_with_limit(self, file: UploadFile) -> bytes:
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        content = b""
        while chunk := await file.read(8192):
            if len(content) + len(chunk) > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size is {max_size // (1024 * 1024)}MB",
                )
            content += chunk
        return content

    async def save(self, content: bytes, filename: str) -> tuple[UUID, Path]:
        file_id = uuid4()
        ext = os.path.splitext(filename)[1].lower()
        file_path = self.uploads_dir / (str(file_id) + ext)
        file_path_str = str(file_path)

        try:
            async with aiofiles.open(file_path_str, "wb") as f:
                await f.write(content)
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file",
            ) from e

        return file_id, file_path

    def cleanup(self, file_path: Path) -> None:
        if file_path.exists():
            file_path.unlink()


file_service = FileService()
