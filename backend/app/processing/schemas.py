"""Normalized page-preserving processing models."""

from typing import Literal

from pydantic import BaseModel, Field

SourceMethod = Literal["ocr", "direct-parse"]


class LayoutBox(BaseModel):
    x0: float = 0
    top: float = 0
    x1: float = 0
    bottom: float = 0


class ExtractedSpan(BaseModel):
    page_number: int = Field(ge=1)
    text: str
    source_method: SourceMethod
    bbox: LayoutBox | None = None
    is_table: bool = False


class NormalizedPage(BaseModel):
    page_number: int = Field(ge=1)
    width: float | None = None
    height: float | None = None
    spans: list[ExtractedSpan] = Field(default_factory=list)


class NormalizedDocument(BaseModel):
    pages: list[NormalizedPage] = Field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def text(self) -> str:
        return "\n\n".join(
            "\n".join(span.text for span in page.spans if span.text) for page in self.pages
        )
