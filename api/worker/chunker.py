MIN_CHUNK_SIZE = 200
MAX_CHUNK_SIZE = 1000
OVERLAP = 50


def semantic_chunk(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para)

        if current_size + para_size > MAX_CHUNK_SIZE and current_chunk:
            chunks.append(" ".join(current_chunk))

            # --- Overlap logic ---
            last_para = current_chunk[-1]
            overlap_start = max(0, len(last_para) - OVERLAP)

            if overlap_start > 0:
                overlapping_text = last_para[overlap_start:]

                # Start the new chunk with this overlap
                current_chunk = [overlapping_text]
                current_size = len(overlapping_text)
            else:
                # If overlap is not meaningful (e.g., paragraph too short)
                current_chunk = []
                current_size = 0

        # Add the current paragraph to the chunk
        current_chunk.append(para)

        current_size += para_size + 1

    # Add any remaining content as the last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # --- Post-processing: merge small chunks ---
    merged_chunks: list[str] = []
    buffer = ""  # Temporarily accumulates small chunks

    for chunk in chunks:
        if not chunk:
            continue

        if len(buffer) + len(chunk) < MIN_CHUNK_SIZE:
            buffer = buffer + " " + chunk if buffer else chunk
        else:
            if buffer:
                merged_chunks.append(buffer)

            if len(chunk) >= MIN_CHUNK_SIZE:
                merged_chunks.append(chunk)
                buffer = ""
            else:
                buffer = chunk

    # If something remains in the buffer, include it only if it's not too small.
    if buffer and len(buffer) >= MIN_CHUNK_SIZE // 2:
        merged_chunks.append(buffer)

    return merged_chunks


def chunk_text(text: str) -> list[dict[str, str | int]]:
    chunks = semantic_chunk(text)
    return [{"content": chunk, "chunk_index": i} for i, chunk in enumerate(chunks)]
