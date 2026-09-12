"""Local-volume document storage behind a swappable abstraction."""

import asyncio
import hashlib
import os
from pathlib import Path
from uuid import uuid4


class StorageError(Exception):
    """Raised when a stored document cannot be accessed safely."""


from contextlib import asynccontextmanager
import typing

class LocalFileStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    async def save(self, filename: str, chunks: list[bytes]) -> tuple[str, str]:
        storage_id = str(uuid4())
        safe_name = Path(filename).name
        relative_path = Path(storage_id) / safe_name
        target = self.root / relative_path
        digest = hashlib.sha256()

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as stream:
                for chunk in chunks:
                    digest.update(chunk)
                    stream.write(chunk)

        await asyncio.to_thread(write)
        return str(relative_path).replace(os.sep, "/"), digest.hexdigest()

    async def save_bytes(self, relative_path: str, content: bytes) -> str:
        target = self._resolve(relative_path)

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        await asyncio.to_thread(write)
        return str(relative_path).replace(os.sep, "/")

    async def delete(self, storage_reference: str) -> None:
        target = self._resolve(storage_reference)
        await asyncio.to_thread(target.unlink, missing_ok=True)
        parent = target.parent
        if parent != self.root:
            await asyncio.to_thread(parent.rmdir)

    async def checksum(self, storage_reference: str) -> str:
        target = self._resolve(storage_reference)

        def read_checksum() -> str:
            digest = hashlib.sha256()
            with target.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()

        try:
            return await asyncio.to_thread(read_checksum)
        except FileNotFoundError as error:
            raise StorageError("stored document is missing") from error

    def _resolve(self, storage_reference: str) -> Path:
        target = (self.root / storage_reference).resolve()
        if self.root not in target.parents:
            raise StorageError("invalid storage reference")
        return target

    @asynccontextmanager
    async def get_local_path(self, storage_reference: str) -> typing.AsyncGenerator[str, None]:
        target = self._resolve(storage_reference)
        yield str(target)
