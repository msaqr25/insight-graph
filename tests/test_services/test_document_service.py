from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from api.models.document import Document, DocumentStatus
from api.services.document_service import DocumentService


class TestDocumentService:
    """Tests for DocumentService."""

    @pytest.fixture
    def document_service(self):
        return DocumentService()

    @pytest.fixture
    def mock_db_session(self):
        session = MagicMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.get = MagicMock()
        return session

    @pytest.mark.asyncio
    async def test_create_document(self, document_service, mock_db_session):
        """Test creating a document."""
        doc_id = uuid4()

        doc = await document_service.create(
            db=mock_db_session,
            file_id=doc_id,
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )

        assert doc.filename == "test.pdf"
        assert doc.content_type == "application/pdf"
        assert doc.size_bytes == 1024
        assert doc.status == DocumentStatus.EXTRACTING
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_commits_transaction(self, document_service, mock_db_session):
        """Test create commits the transaction."""
        await document_service.create(
            db=mock_db_session,
            file_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )

        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_document(self, document_service):
        """Test getting a document by ID."""
        doc_id = uuid4()
        expected_doc = Document(
            id=doc_id,
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )

        mock_db_session = MagicMock()
        mock_db_session.get = AsyncMock(return_value=expected_doc)

        result = await document_service.get(mock_db_session, doc_id)

        mock_db_session.get.assert_called_once_with(Document, doc_id)
        assert result == expected_doc

    @pytest.mark.asyncio
    async def test_get_returns_none(self, document_service):
        """Test get returns None when not found."""
        doc_id = uuid4()
        mock_db_session = MagicMock()
        mock_db_session.get = AsyncMock(return_value=None)

        result = await document_service.get(mock_db_session, doc_id)

        assert result is None
