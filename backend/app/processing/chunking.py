"""Document text chunking with page-preserving metadata."""

from dataclasses import dataclass
from typing import Any

from app.processing.schemas import NormalizedDocument


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]


class TextChunker:
    """Splits document page text into configurable size and overlap chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self.chunk_size = max(50, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    def chunk_document(
        self,
        normalized: NormalizedDocument,
        user_id: str,
        document_id: str,
        document_name: str,
        language: str = "en",
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        global_chunk_index = 0

        for page in normalized.pages:
            page_text = " ".join(span.text.strip() for span in page.spans if span.text.strip()).strip()
            if not page_text:
                continue

            page_chunks = self._slice_text(page_text)
            for text_segment in page_chunks:
                chunk_id = f"chunk_{document_id}_p{page.page_number}_{global_chunk_index}"
                metadata = {
                    "user_id": user_id,
                    "document_id": document_id,
                    "document_name": document_name,
                    "page_number": page.page_number,
                    "language": language,
                    "chunk_index": global_chunk_index,
                }
                chunks.append(DocumentChunk(chunk_id=chunk_id, text=text_segment, metadata=metadata))
                global_chunk_index += 1

        return chunks

    def _slice_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        segments: list[str] = []
        start = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = start + self.chunk_size
            segment = text[start:end].strip()
            if segment:
                segments.append(segment)
            start += step
            if start >= len(text):
                break

        return segments
