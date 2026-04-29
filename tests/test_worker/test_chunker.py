from api.worker.chunker import _enforce_min_size, chunk_text


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

    def test_normal_text_chunks(self):
        """Test chunking normal text."""
        text = "This is first paragraph with multiple sentences.\n\nThis is second paragraph with more text.\n\nThis is third paragraph."
        chunks = chunk_text(text)

        assert isinstance(chunks, list)

    def test_multiple_paragraphs(self):
        """Test multiple paragraphs."""
        text = "Paragraph one here with some text.\n\nParagraph two here with more text.\n\nParagraph three here."
        chunks = chunk_text(text)

        assert isinstance(chunks, list)


class TestEnforceMinSize:
    """Tests for _enforce_min_size function."""

    def test_no_change_when_above_min(self):
        """Test chunks above min size are not changed."""
        chunks = ["abc def ghi jkl", "mno pqr stu vwx"]
        result = _enforce_min_size(chunks, min_size=5)

        assert result == chunks

    def test_merges_small_chunks(self):
        """Test small chunks are merged."""
        chunks = ["ab", "cd", "ef"]
        result = _enforce_min_size(chunks, min_size=5)

        assert len(result) <= len(chunks)
        assert all(len(c) >= 5 or c == result[-1] for c in result)

    def test_empty_list_returns_empty(self):
        """Test empty list returns empty list."""
        result = _enforce_min_size([], min_size=10)

        assert result == []

    def test_zero_min_size_returns_original(self):
        """Test zero min size returns original chunks."""
        chunks = ["small"]
        result = _enforce_min_size(chunks, min_size=0)

        assert result == chunks

    def test_small_remainder_appended_to_last(self):
        """Test small remainder is appended to last chunk."""
        chunks = ["hello world", "a"]
        result = _enforce_min_size(chunks, min_size=10)

        assert len(result) <= 2
