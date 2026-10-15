"""Document chunking for retrieval: whole lines, intact table rows, page metadata.

* Text is packed line by line up to ``chunk_size`` characters, never cutting a
  line or a word; consecutive chunks share up to ``chunk_overlap`` characters
  of trailing lines so a value next to a chunk boundary keeps its label.
* Table rows stay whole, and every table chunk repeats the header row, so
  "PHYSICS | 100 | 091" is always read together with "Subject | Max | Obtained".
  Plain-text copies of table rows are dropped (the parser emits both).
* Each chunk has an ``embed_text`` that adds the document type and name, so a
  question about "my income certificate" matches that document's chunks; the
  stored text stays exactly what the document says.

Metadata on every chunk: user, document id/name/type, page, chunk index,
whether it is a table, and how the text was obtained (OCR or parsing).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.processing.schemas import ExtractedSpan, NormalizedDocument

_TYPE_LABELS = {
    "CLASS_10_MARKSHEET": "Class 10 marksheet",
    "CLASS_12_MARKSHEET": "Class 12 marksheet",
    "CASTE_VALIDITY_CERTIFICATE": "caste validity certificate",
    "NON_CREAMY_LAYER_CERTIFICATE": "non-creamy layer certificate",
}


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    embed_text: str = field(default="")

    def __post_init__(self) -> None:
        if not self.embed_text:
            self.embed_text = self.text


def _compact(text: str) -> str:
    return re.sub(r"[\s|]+", "", text).casefold()


def type_label(document_type: str) -> str:
    if document_type in _TYPE_LABELS:
        return _TYPE_LABELS[document_type]
    return document_type.replace("_", " ").lower() if document_type != "UNKNOWN" else "document"


class TextChunker:
    """Splits page text into line-preserving chunks with page metadata."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self.chunk_size = max(50, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    def chunk_document(
        self,
        normalized: NormalizedDocument,
        user_id: str,
        document_id: str,
        document_name: str,
        document_type: str = "UNKNOWN",
        language: str = "en",
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        context = f"{type_label(document_type or 'UNKNOWN')} ({document_name or 'document'})"

        for page in normalized.pages:
            tables = [s for s in page.spans if s.is_table and s.text.strip()]
            table_rows = {
                _compact(row)
                for span in tables
                for row in span.text.splitlines()
                if row.strip(" |")
            }
            lines = [
                line.strip()
                for span in page.spans
                if not span.is_table
                for line in span.text.splitlines()
                if line.strip() and _compact(line) not in table_rows
            ]
            method = _method(page.spans)
            pieces: list[tuple[str, bool]] = [(text, False) for text in self._pack(lines)]
            for span in tables:
                pieces += [(text, True) for text in self._pack_table(span.text)]
            for text, is_table in pieces:
                index = len(chunks)
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"chunk_{document_id}_p{page.page_number}_{index}",
                        text=text,
                        embed_text=f"{context}, page {page.page_number}:\n{text}",
                        metadata={
                            "user_id": user_id,
                            "document_id": document_id,
                            "document_name": document_name or "document",
                            "document_type": document_type or "UNKNOWN",
                            "source_type": "document",
                            "page_number": page.page_number,
                            "language": language,
                            "chunk_index": index,
                            "is_table": is_table,
                            "extraction_method": method,
                        },
                    )
                )
        return chunks

    def _pack(self, lines: list[str]) -> list[str]:
        """Whole lines up to ``chunk_size``; overlap repeats trailing lines."""
        chunks: list[str] = []
        current: list[str] = []
        size = 0
        for line in self._split_long(lines):
            if current and size + len(line) + 1 > self.chunk_size:
                chunks.append("\n".join(current))
                carried: list[str] = []
                carried_size = 0
                for previous in reversed(current):
                    if carried_size + len(previous) + 1 > self.chunk_overlap:
                        break
                    carried.insert(0, previous)
                    carried_size += len(previous) + 1
                current, size = carried, carried_size
            current.append(line)
            size += len(line) + 1
        if current:
            chunks.append("\n".join(current))
        return chunks

    def _split_long(self, lines: list[str]) -> list[str]:
        """Break lines longer than a chunk at word boundaries (long paragraphs)."""
        out: list[str] = []
        for line in lines:
            while len(line) > self.chunk_size:
                cut = line.rfind(" ", 0, self.chunk_size)
                cut = cut if cut > self.chunk_size // 2 else self.chunk_size
                out.append(line[:cut].strip())
                line = line[cut:].strip()
            if line:
                out.append(line)
        return out

    def _pack_table(self, text: str) -> list[str]:
        rows = [row.strip() for row in text.splitlines() if row.strip(" |")]
        if not rows:
            return []
        header, body = rows[0], rows[1:]
        if not body:
            return [header]
        chunks: list[str] = []
        current: list[str] = []
        size = len(header)
        for row in body:
            if current and size + len(row) + 1 > self.chunk_size:
                chunks.append("\n".join([header, *current]))
                current, size = [], len(header)
            current.append(row)
            size += len(row) + 1
        if current:
            chunks.append("\n".join([header, *current]))
        return chunks


def _method(spans: list[ExtractedSpan]) -> str:
    methods = {span.source_method for span in spans}
    return "ocr" if methods == {"ocr"} else ("mixed" if "ocr" in methods else "direct-parse")
