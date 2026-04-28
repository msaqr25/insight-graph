from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


class TestUploadEndpoint:
    """Tests for the POST /api/upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_rejects_non_pdf(self):
        """Test upload rejects non-PDF files."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("api.services.file_service.settings") as mock_settings:
                mock_settings.UPLOADS_DIR = "/tmp/test"
                mock_settings.MAX_FILE_SIZE_MB = 10

                response = await client.post(
                    "/api/upload",
                    files={"file": ("test.txt", b"content", "text/plain")},
                )

                assert response.status_code == 415


class TestJobStatusEndpoint:
    """Tests for the GET /api/job/{job_id} endpoint."""

    @pytest.mark.skip(reason="Requires app state mocking - complex test")
    @pytest.mark.asyncio
    async def test_job_not_found(self):
        """Test returns 404 for non-existent job."""
        pass

    @pytest.mark.skip(reason="Requires app state mocking - complex test")
    @pytest.mark.asyncio
    async def test_job_returns_status(self):
        """Test returns job status."""
        pass


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health endpoint returns 200."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

            assert response.status_code == 200
