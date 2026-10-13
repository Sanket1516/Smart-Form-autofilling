"""Local-volume document storage."""

import asyncio
import hashlib
import os
import shutil
import typing
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4


class StorageError(Exception):
    """Raised when a stored document cannot be accessed safely."""


class LocalFileStorage:
    """Stores each upload in its own random directory below ``root``."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    async def save(self, filename: str, chunks: list[bytes]) -> tuple[str, str]:
        relative_path = Path(str(uuid4())) / _safe_name(filename)
        target = self.root / relative_path
        digest = hashlib.sha256()

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as stream:
                for chunk in chunks:
                    digest.update(chunk)
                    stream.write(chunk)

        await asyncio.to_thread(write)
        return relative_path.as_posix(), digest.hexdigest()

    async def save_bytes(self, relative_path: str, content: bytes) -> str:
        target = self._resolve(relative_path)

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        await asyncio.to_thread(write)
        return Path(relative_path).as_posix()

    async def read_bytes(self, storage_reference: str) -> bytes:
        target = self._resolve(storage_reference)
        try:
            return await asyncio.to_thread(target.read_bytes)
        except FileNotFoundError as error:
            raise StorageError("stored document is missing") from error

    async def delete(self, storage_reference: str) -> None:
        """Delete a stored file and its per-upload directory once that directory is empty."""
        target = self._resolve(storage_reference)
        await asyncio.to_thread(target.unlink, missing_ok=True)
        parent = target.parent
        if parent.parent == self.root and parent.is_dir() and not any(parent.iterdir()):
            await asyncio.to_thread(shutil.rmtree, parent, True)

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
        if not target.exists():
            raise StorageError("stored document is missing")
        yield str(target)


def _safe_name(filename: str) -> str:
    """Keep a readable basename but strip path separators and control characters."""
    name = Path(filename).name
    name = "".join(ch for ch in name if ch.isprintable() and ch not in '<>:"/\\|?*')
    name = name.strip(" .") or "document"
    stem, suffix = os.path.splitext(name)
    return f"{stem[:100]}{suffix[:10]}"
