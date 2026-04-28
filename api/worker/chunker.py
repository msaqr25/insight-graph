from api.config import settings


def semantic_chunk(text: str) -> list[str]:
    min_size = settings.CHUNK_MIN_SIZE
    max_size = settings.CHUNK_MAX_SIZE
    overlap = settings.CHUNK_OVERLAP

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para)

        if para_size > max_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                last_para = current_chunk[-1]
                overlap_start = max(0, len(last_para) - overlap)
                if overlap_start > 0:
                    overlapping_text = last_para[overlap_start:]
                    current_chunk = [overlapping_text]
                    current_size = len(overlapping_text)
                else:
                    current_chunk = []
                    current_size = 0

            parts = split_oversized_paragraph(para, max_size, overlap)
            for part in parts[:-1]:
                if part:
                    chunks.append(part)
            current_chunk.append(parts[-1])
            current_size = len(parts[-1]) + 1
            continue

        if current_size + para_size > max_size and current_chunk:
            chunks.append(" ".join(current_chunk))

            last_para = current_chunk[-1]
            overlap_start = max(0, len(last_para) - overlap)

            if overlap_start > 0:
                overlapping_text = last_para[overlap_start:]
                current_chunk = [overlapping_text]
                current_size = len(overlapping_text)
            else:
                current_chunk = []
                current_size = 0

        current_chunk.append(para)
        current_size += para_size + 1

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    merged_chunks: list[str] = []
    buffer = ""

    for chunk in chunks:
        if not chunk:
            continue

        if len(buffer) + len(chunk) < min_size:
            buffer = buffer + " " + chunk if buffer else chunk
        else:
            if buffer:
                merged_chunks.append(buffer)

            if len(chunk) >= min_size:
                merged_chunks.append(chunk)
                buffer = ""
            else:
                buffer = chunk

    if buffer and len(buffer) >= min_size // 2:
        merged_chunks.append(buffer)

    return merged_chunks


def split_oversized_paragraph(para: str, max_size: int, overlap: int) -> list[str]:
    parts = []
    start = 0
    text_len = len(para)

    while start < text_len:
        end = min(start + max_size, text_len)

        if start > 0 and start >= overlap:
            search_start = start - overlap
            search_end = start
            space_idx = para.rfind(" ", search_start, search_end)
            if space_idx > search_start:
                end = space_idx

        parts.append(para[start:end])
        start = end

    return parts if parts else [para]


def chunk_text(text: str) -> list[dict[str, str | int]]:
    chunks = semantic_chunk(text)
    return [{"content": chunk, "chunk_index": i} for i, chunk in enumerate(chunks)]
