"""Storage abstraction shared by the local and Cloudinary backends."""

import typing
from contextlib import asynccontextmanager


class DocumentStorage(typing.Protocol):
    async def save(self, filename: str, chunks: list[bytes]) -> tuple[str, str]:
        """Save a document. Returns (storage_reference, sha256 checksum)."""
        ...

    async def save_bytes(self, relative_path: str, content: bytes) -> str:
        """Save derived bytes (e.g. normalized JSON). Returns the storage reference."""
        ...

    async def read_bytes(self, storage_reference: str) -> bytes:
        """Return the stored bytes."""
        ...

    async def delete(self, storage_reference: str) -> None:
        """Delete a stored object. Missing objects are not an error."""
        ...

    async def checksum(self, storage_reference: str) -> str:
        """Return the SHA-256 checksum of the stored bytes."""
        ...

    @asynccontextmanager
    async def get_local_path(self, storage_reference: str) -> typing.AsyncGenerator[str, None]:
        """Yield a local filesystem path to the stored document."""
        yield ""
