import typing
import typing_extensions
from contextlib import asynccontextmanager

class DocumentStorage(typing.Protocol):
    """Abstract interface for document storage."""

    async def save(self, filename: str, chunks: list[bytes]) -> tuple[str, str]:
        """Save a document from chunks. Returns (storage_reference, checksum)."""
        ...

    async def save_bytes(self, relative_path: str, content: bytes) -> str:
        """Save a document from bytes. Returns storage_reference."""
        ...

    async def delete(self, storage_reference: str) -> None:
        """Delete a document by its storage reference."""
        ...

    async def checksum(self, storage_reference: str) -> str:
        """Compute or retrieve the SHA256 checksum of the stored document."""
        ...

    @asynccontextmanager
    async def get_local_path(self, storage_reference: str) -> typing.AsyncGenerator[str, None]:
        """
        Async context manager that yields a local file path to the document.
        For local storage, it yields the physical path.
        For remote storage, it downloads to a temp file, yields it, and cleans up.
        """
        yield ""
