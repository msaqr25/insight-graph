from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from api.services.file_service import FileService


class TestFileService:
    """Tests for FileService."""

    @pytest.fixture
    def file_service(self, tmp_upload_dir):
        with patch("api.services.file_service.settings") as mock_settings:
            mock_settings.UPLOADS_DIR = str(tmp_upload_dir)
            mock_settings.MAX_FILE_SIZE_MB = 10
            service = FileService()
            return service

    @pytest.mark.asyncio
    async def test_validate_accepts_pdf(self, file_service):
        """Test validate accepts valid PDF file."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "application/pdf"
        mock_file.filename = "test.pdf"

        await file_service.validate(mock_file)

    @pytest.mark.asyncio
    async def test_validate_rejects_non_pdf(self, file_service):
        """Test validate rejects non-PDF file."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "text/plain"
        mock_file.filename = "test.txt"

        with pytest.raises(HTTPException) as exc_info:
            await file_service.validate(mock_file)

        assert exc_info.value.status_code == 415

    @pytest.mark.asyncio
    async def test_validate_rejects_missing_filename(self, file_service):
        """Test validate rejects missing filename."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "application/pdf"
        mock_file.filename = None

        with pytest.raises(HTTPException) as exc_info:
            await file_service.validate(mock_file)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_validate_rejects_invalid_extension(self, file_service):
        """Test validate rejects file without .pdf extension."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "application/pdf"
        mock_file.filename = "test.txt"

        with pytest.raises(HTTPException) as exc_info:
            await file_service.validate(mock_file)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_read_with_limit_returns_content(self, file_service):
        """Test read_with_limit returns file content."""
        content = b"test file content"
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(side_effect=[content, b""])

        result = await file_service.read_with_limit(mock_file)

        assert result == content

    @pytest.mark.asyncio
    async def test_read_with_limit_enforces_size(self, file_service):
        """Test read_with_limit raises when file too large."""
        content = b"x" * (11 * 1024 * 1024)
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(side_effect=[content, b""])

        with pytest.raises(HTTPException) as exc_info:
            await file_service.read_with_limit(mock_file)

        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_save_returns_uuid_and_path(self, file_service, tmp_upload_dir):
        """Test save returns UUID and file path."""
        content = b"test content"
        file_id, file_path = await file_service.save(content, "test.pdf")

        assert file_id is not None
        assert isinstance(file_path, Path)

    @pytest.mark.asyncio
    async def test_save_creates_file(self, file_service, tmp_upload_dir):
        """Test save creates file on disk."""
        content = b"test file content"

        await file_service.save(content, "test.pdf")

        files = list(tmp_upload_dir.glob("*.pdf"))
        assert len(files) == 1

    @pytest.mark.asyncio
    async def test_save_cleans_up_on_error(self, file_service, tmp_upload_dir):
        """Test save cleans up file on error."""
        with pytest.raises((ValueError, TypeError)):
            await file_service.save(b"content", None)  # type: ignore[arg-type]

        files = list(tmp_upload_dir.glob("*.pdf"))
        assert len(files) == 0

    def test_cleanup_removes_file(self, file_service, tmp_path):
        """Test cleanup removes file."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test")

        file_service.cleanup(test_file)

        assert not test_file.exists()


class TestFileServiceIntegration:
    """Integration tests for FileService."""

    @pytest.fixture
    def file_service(self, tmp_path):
        with patch("api.services.file_service.settings") as mock_settings:
            upload_dir = tmp_path / "uploads"
            upload_dir.mkdir()
            mock_settings.UPLOADS_DIR = str(upload_dir)
            mock_settings.MAX_FILE_SIZE_MB = 10
            service = FileService()
            yield service

    @pytest.mark.asyncio
    async def test_full_upload_flow(self, file_service):
        """Test complete upload flow."""
        content = b"PDF content here"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "application/pdf"
        mock_file.filename = "document.pdf"

        await file_service.validate(mock_file)

        mock_file.read = AsyncMock(side_effect=[content, b""])
        file_content = await file_service.read_with_limit(mock_file)

        file_id, file_path = await file_service.save(file_content, "document.pdf")

        assert file_path.exists()
        assert file_path.read_bytes() == content

        file_service.cleanup(file_path)
        assert not file_path.exists()
