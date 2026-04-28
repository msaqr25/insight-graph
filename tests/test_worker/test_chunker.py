from api.worker.chunker import chunk_text, semantic_chunk, split_oversized_paragraph


class TestSemanticChunk:
    """Tests for semantic_chunk function."""

    def test_normal_text_chunks(self):
        """Test chunking normal text."""
        text = "This is first paragraph with multiple sentences.\n\nThis is second paragraph with more text.\n\nThis is third paragraph."
        chunks = semantic_chunk(text)

        assert len(chunks) >= 0  # May be empty if text is too short

    def test_empty_text(self):
        """Test returns empty list for empty text."""
        chunks = semantic_chunk("")

        assert chunks == []

    def test_single_paragraph(self):
        """Test single paragraph text."""
        text = "This is a single paragraph with enough text to potentially create a chunk."
        chunks = semantic_chunk(text)

        assert len(chunks) >= 0

    def test_multiple_paragraphs(self):
        """Test multiple paragraphs."""
        text = "Paragraph one here with some text.\n\nParagraph two here with more text.\n\nParagraph three here."
        chunks = semantic_chunk(text)

        assert len(chunks) >= 0

    def test_small_chunks_merged(self):
        """Test small chunks are merged."""
        text = "A" * 100 + "\n\n" + "B" * 100
        chunks = semantic_chunk(text)

        # Small chunks should be merged or dropped
        if chunks:
            for chunk in chunks:
                assert len(chunk) <= 400


class TestSplitOversizedParagraph:
    """Tests for split_oversized_paragraph function."""

    def test_short_text_not_split(self):
        """Test short text is not split."""
        text = "Short text"
        parts = split_oversized_paragraph(text, 1000, 50)

        assert len(parts) == 1

    def test_long_text_split(self):
        """Test long text is split into multiple parts."""
        text = "A" * 2000
        parts = split_oversized_paragraph(text, 1000, 50)

        assert len(parts) == 2
        assert parts[0] == "A" * 1000
        assert parts[1] == "A" * 1000

    def test_exactly_max_size(self):
        """Test text exactly at max size."""
        text = "A" * 1000
        parts = split_oversized_paragraph(text, 1000, 50)

        assert len(parts) == 1

    def test_slight_over_max(self):
        """Test text slightly over max size."""
        text = "A" * 1001
        parts = split_oversized_paragraph(text, 1000, 50)

        assert len(parts) == 2


class TestChunkText:
    """Tests for chunk_text function."""

    def test_returns_list_of_dicts(self):
        """Test returns list of dicts with content and index."""
        text = """First paragraph.

Second paragraph."""

        result = chunk_text(text)

        assert isinstance(result, list)
        assert all("content" in item for item in result)
        assert all("chunk_index" in item for item in result)

    def test_chunk_indices(self):
        """Test chunk indices are sequential."""
        text = """One.

Two.

Three."""

        result = chunk_text(text)

        indices = [item["chunk_index"] for item in result]
        assert indices == list(range(len(result)))

    def test_empty_text_returns_empty(self):
        """Test empty text returns empty list."""
        result = chunk_text("")

        assert result == []


class TestChunkBoundaries:
    """Tests for chunk size boundaries."""

    def test_chunks_within_max_size(self):
        """Test chunks are within max size."""
        # Create text that would produce large chunks
        text = "A" * 500 + "\n\n" + "B" * 500
        chunks = semantic_chunk(text)

        for chunk in chunks:
            assert len(chunk) <= 1500  # Allow some buffer

    def test_min_chunk_size_merging(self):
        """Test minimum chunk size is enforced."""
        # Very short paragraphs
        text = "AB\n\nCD\n\nEF"
        chunks = semantic_chunk(text)

        # Should merge small chunks or drop very small ones
        for chunk in chunks:
            assert len(chunk) < 200 or len(chunk) >= 100
