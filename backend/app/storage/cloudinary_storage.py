"""Cloudinary storage for raw documents.

New uploads use delivery type ``private`` so a document can only be fetched
through a signed, short-lived API URL. References created before this change
were stored with the public ``upload`` type and carry no prefix; they keep
working through the same signed-URL path.
"""

import asyncio
import hashlib
import os
import tempfile
import typing
from contextlib import asynccontextmanager
from pathlib import Path

import cloudinary  # type: ignore[import-untyped]
import cloudinary.uploader  # type: ignore[import-untyped]
import cloudinary.utils  # type: ignore[import-untyped]
import httpx

from app.storage.local import StorageError

_PRIVATE_PREFIX = "private:"


def _split(reference: str) -> tuple[str, str]:
    if reference.startswith(_PRIVATE_PREFIX):
        return reference[len(_PRIVATE_PREFIX) :], "private"
    return reference, "upload"


class CloudinaryStorage:
    def __init__(self, cloud_name: str, api_key: str, api_secret: str) -> None:
        cloudinary.config(
            cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True
        )

    async def save(self, filename: str, chunks: list[bytes]) -> tuple[str, str]:
        content = b"".join(chunks)
        digest = hashlib.sha256(content).hexdigest()

        def upload() -> dict:
            return cloudinary.uploader.upload(
                content,
                resource_type="raw",
                type="private",
                use_filename=True,
                unique_filename=True,
                filename_override=Path(filename).name,
            )

        response = await asyncio.to_thread(upload)
        return f"{_PRIVATE_PREFIX}{response['public_id']}", digest

    async def save_bytes(self, relative_path: str, content: bytes) -> str:
        public_id, _ = _split(relative_path)

        def upload() -> dict:
            return cloudinary.uploader.upload(
                content, resource_type="raw", type="private", public_id=public_id, overwrite=True
            )

        response = await asyncio.to_thread(upload)
        return f"{_PRIVATE_PREFIX}{response['public_id']}"

    async def read_bytes(self, storage_reference: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(self._signed_url(storage_reference))
        if response.status_code != 200:
            raise StorageError("stored document is missing or inaccessible")
        return response.content

    async def delete(self, storage_reference: str) -> None:
        public_id, delivery_type = _split(storage_reference)
        await asyncio.to_thread(
            cloudinary.uploader.destroy, public_id, resource_type="raw", type=delivery_type
        )

    async def checksum(self, storage_reference: str) -> str:
        return hashlib.sha256(await self.read_bytes(storage_reference)).hexdigest()

    @asynccontextmanager
    async def get_local_path(self, storage_reference: str) -> typing.AsyncGenerator[str, None]:
        public_id, _ = _split(storage_reference)
        fd, temp_path = tempfile.mkstemp(suffix=Path(public_id).suffix)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(await self.read_bytes(storage_reference))
            yield temp_path
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    @staticmethod
    def _signed_url(storage_reference: str) -> str:
        public_id, delivery_type = _split(storage_reference)
        return cloudinary.utils.private_download_url(
            public_id, "", resource_type="raw", type=delivery_type, attachment=False
        )
