from langchain_text_splitters import RecursiveCharacterTextSplitter

from api.config import settings


def chunk_text(text: str) -> list[dict[str, str | int]]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_MAX_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
    )
    text = _clean_text(text)
    chunks = text_splitter.split_text(text)
    chunks = _enforce_min_size(chunks)
    return [{"content": chunk, "chunk_index": i} for i, chunk in enumerate(chunks)]


def _clean_text(text: str) -> str:
    return (
        text.replace("\x00", "").encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    )


def _enforce_min_size(chunks: list[str], min_size: int = settings.CHUNK_MIN_SIZE) -> list[str]:
    if min_size <= 0:
        return chunks

    merged = []
    buffer = ""

    for chunk in chunks:
        buffer += chunk
        if len(buffer) >= min_size:
            merged.append(buffer)
            buffer = ""

    if len(buffer) >= min_size // 2:
        if merged:
            merged[-1] += buffer
        else:
            merged.append(buffer)
    elif buffer and merged:
        merged[-1] += buffer

    return merged if merged else chunks
