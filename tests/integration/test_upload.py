import pytest


class TestUploadEndpoint:
    """Integration tests for document upload."""

    @pytest.mark.asyncio
    async def test_upload_rejects_non_pdf(self, client):
        """Test upload rejects non-PDF files."""
        response = await client.post(
            "/api/upload",
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 415

    @pytest.mark.asyncio
    async def test_upload_requires_filename(self, client):
        """Test upload rejects missing filename."""
        response = await client.post(
            "/api/upload",
            files={"file": ("", b"content", "application/pdf")},
        )

        assert response.status_code in (400, 422)
