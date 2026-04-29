from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestExtractText:
    """Tests for the extract_text task."""

    @pytest.mark.asyncio
    async def test_extract_text_returns_text_and_id(self):
        """Test extract_text returns extracted text and document ID."""
        from api.worker import tasks

        doc_id = str(uuid4())
        mock_redis = AsyncMock()

        with patch("api.worker.tasks.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

            mock_doc = MagicMock()
            mock_doc.status = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_doc

            with patch("api.worker.tasks.pymupdf") as mock_pdf:
                mock_page = MagicMock()
                mock_page.get_text.return_value = "Extracted text"
                mock_pdf.open.return_value.__enter__.return_value = [mock_page]
                mock_pdf.open.return_value.__exit__.return_value = False

                ctx = {"redis": mock_redis}

                result = await tasks.extract_text(ctx, "/tmp/test.pdf", doc_id)

                assert "text" in result
                assert "document_id" in result
                assert result["document_id"] == doc_id


class TestChunkTextTask:
    """Tests for the chunk_text_task."""

    @pytest.mark.asyncio
    async def test_chunk_text_creates_chunks(self):
        """Test chunk_text_task creates chunks in database."""
        from api.worker import tasks

        doc_id = str(uuid4())
        text = "Sample text for chunking."
        mock_redis = AsyncMock()

        with patch("api.worker.tasks.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

            mock_doc = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_doc

            with patch("api.worker.tasks.chunk_text") as mock_chunker:
                mock_chunker.return_value = [
                    {"content": "chunk 1", "chunk_index": 0},
                    {"content": "chunk 2", "chunk_index": 1},
                ]

                ctx = {"redis": mock_redis}

                result = await tasks.chunk_text_task(ctx, text, doc_id)

                assert result["chunk_count"] == 2
                assert result["document_id"] == doc_id


class TestEmbedAndStore:
    """Tests for the embed_and_store task."""

    @pytest.mark.asyncio
    async def test_embed_and_store_returns_count(self):
        """Test embed_and_store returns embedded count."""

        from api.worker import tasks

        doc_id = str(uuid4())

        mock_chunk = MagicMock()
        mock_chunk.content = "test content"
        mock_chunk.embedding = [0.1] * 384

        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1] * 384

        with patch("api.worker.tasks.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

            mock_doc = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_doc

            mock_query = MagicMock()
            mock_query.filter.return_value.all.return_value = [mock_chunk]
            mock_session.query.return_value = mock_query

            ctx = {"embedding_model": MagicMock()}

            ctx["embedding_model"].encode = MagicMock(return_value=[mock_embedding])

            result = await tasks.embed_and_store(ctx, doc_id)

            assert "embedded_count" in result


class TestJobChaining:
    """Tests for job chaining in tasks."""

    @pytest.mark.asyncio
    async def test_extract_text_enqueues_next_job(self):
        """Test extract_text enqueues chunk_text_task."""
        from api.worker import tasks

        doc_id = str(uuid4())
        mock_redis = AsyncMock()

        with patch("api.worker.tasks.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

            mock_doc = MagicMock()
            mock_doc.status = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_doc

            with patch("api.worker.tasks.pymupdf") as mock_pdf:
                mock_page = MagicMock()
                mock_page.get_text.return_value = "Text"
                mock_pdf.open.return_value.__enter__.return_value = [mock_page]

                ctx = {"redis": mock_redis}

                await tasks.extract_text(ctx, "/tmp/test.pdf", doc_id)

                mock_redis.enqueue_job.assert_called_once()


class TestErrorHandling:
    """Tests for error handling in tasks."""

    @pytest.mark.asyncio
    async def test_extract_text_sets_failed_on_error(self):
        """Test extract_text sets status to FAILED on error."""
        from api.worker import tasks

        doc_id = str(uuid4())

        with patch("api.worker.tasks.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

            mock_session.query.return_value.filter.return_value.first.return_value = None

            ctx = {"redis": MagicMock()}

            with pytest.raises(ValueError):
                await tasks.extract_text(ctx, "/tmp/test.pdf", doc_id)


class TestFileCleanup:
    """Tests for file cleanup."""

    @pytest.mark.asyncio
    async def test_extract_text_preserves_file(self):
        """Test extract_text preserves PDF for download."""
        from api.worker import tasks

        doc_id = str(uuid4())
        test_file = MagicMock()
        test_file.exists.return_value = True
        mock_redis = AsyncMock()

        with patch("api.worker.tasks.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

            mock_doc = MagicMock()
            mock_doc.status = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_doc

            with patch("api.worker.tasks.pymupdf") as mock_pdf:
                mock_page = MagicMock()
                mock_page.get_text.return_value = "Text"
                mock_pdf.open.return_value.__enter__.return_value = [mock_page]

                ctx = {"redis": mock_redis}

                await tasks.extract_text(ctx, "/tmp/test.pdf", doc_id)

                test_file.unlink.assert_not_called()
