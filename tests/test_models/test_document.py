from uuid import uuid4

from api.models.document import Document, DocumentChunk, DocumentStatus


class TestDocumentStatus:
    """Tests for DocumentStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert DocumentStatus.PENDING.value is not None
        assert DocumentStatus.EXTRACTING.value is not None
        assert DocumentStatus.CHUNKING.value is not None
        assert DocumentStatus.EMBEDDING.value is not None
        assert DocumentStatus.COMPLETED.value is not None
        assert DocumentStatus.FAILED.value is not None

    def test_status_order(self):
        """Test status can be compared."""
        assert DocumentStatus.PENDING != DocumentStatus.COMPLETED
        assert DocumentStatus.EXTRACTING == DocumentStatus.EXTRACTING


class TestDocument:
    """Tests for Document model."""

    def test_create_document(self):
        """Test creating a Document instance."""
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            status=DocumentStatus.PENDING,
        )

        assert doc.id == doc_id
        assert doc.filename == "test.pdf"
        assert doc.content_type == "application/pdf"
        assert doc.size_bytes == 1024
        assert doc.status == DocumentStatus.PENDING

    def test_default_status(self):
        """Test default status is PENDING."""
        from api.models.document import DocumentStatus

        doc = Document(
            id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            status=DocumentStatus.PENDING,
        )

        assert doc.status == DocumentStatus.PENDING

    def test_tablename(self):
        """Test table name is set correctly."""
        assert Document.__tablename__ == "documents"


class TestDocumentChunk:
    """Tests for DocumentChunk model."""

    def test_create_chunk(self):
        """Test creating a DocumentChunk instance."""
        doc_id = uuid4()
        chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=0,
            content="Sample chunk content",
            embedding=[0.1] * 384,
        )

        assert chunk.document_id == doc_id
        assert chunk.chunk_index == 0
        assert chunk.content == "Sample chunk content"
        assert chunk.embedding == [0.1] * 384

    def test_chunk_with_null_embedding(self):
        """Test chunk can have null embedding."""
        doc_id = uuid4()
        chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=0,
            content="Sample chunk content",
            embedding=None,
        )

        assert chunk.embedding is None

    def test_chunk_tablename(self):
        """Test chunk table name is set correctly."""
        assert DocumentChunk.__tablename__ == "document_chunks"


class TestDocumentRelationship:
    """Tests for Document to DocumentChunk relationship."""

    def test_document_has_chunks_relationship(self):
        """Test Document has chunks relationship."""
        doc = Document(
            id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )

        assert hasattr(doc, "chunks")

    def test_chunk_has_document_relationship(self):
        """Test DocumentChunk has document relationship."""
        chunk = DocumentChunk(
            document_id=uuid4(),
            chunk_index=0,
            content="test",
        )

        assert hasattr(chunk, "document")
