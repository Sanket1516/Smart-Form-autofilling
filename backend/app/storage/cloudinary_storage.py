import asyncio
import hashlib
import os
import tempfile
import typing
from contextlib import asynccontextmanager
from pathlib import Path

import cloudinary # type: ignore
import cloudinary.uploader # type: ignore
import httpx

from app.storage.local import StorageError

class CloudinaryStorage:
    def __init__(self, cloud_name: str, api_key: str, api_secret: str) -> None:
        self.cloud_name = cloud_name
        if cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )

    async def save(self, filename: str, chunks: list[bytes]) -> tuple[str, str]:
        """Save a document to Cloudinary and return its public ID and checksum."""
        digest = hashlib.sha256()
        for chunk in chunks:
            digest.update(chunk)
            
        full_content = b"".join(chunks)

        def upload():
            return cloudinary.uploader.upload(
                full_content,
                resource_type="raw",
                type="authenticated",
                use_filename=True,
                unique_filename=True,
                filename_override=Path(filename).name
            )

        response = await asyncio.to_thread(upload)
        return response["public_id"], digest.hexdigest()

    async def save_bytes(self, relative_path: str, content: bytes) -> str:
        """Save bytes directly (used for normalized JSON etc.)."""
        def upload():
            return cloudinary.uploader.upload(
                content,
                resource_type="raw",
                type="authenticated",
                public_id=relative_path,
                overwrite=True
            )
            
        response = await asyncio.to_thread(upload)
        return response["public_id"]

    async def delete(self, storage_reference: str) -> None:
        """Delete an asset from Cloudinary."""
        def destroy():
            return cloudinary.uploader.destroy(storage_reference, resource_type="raw", type="authenticated")
            
        await asyncio.to_thread(destroy)

    async def checksum(self, storage_reference: str) -> str:
        """Fetch the file and compute its checksum."""
        url = cloudinary.utils.cloudinary_url(storage_reference, resource_type="raw", type="authenticated", sign_url=True)[0]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise StorageError("stored document is missing or inaccessible")
                
            digest = hashlib.sha256()
            digest.update(response.content)
            return digest.hexdigest()

    @asynccontextmanager
    async def get_local_path(self, storage_reference: str) -> typing.AsyncGenerator[str, None]:
        """Download to a temp file, yield it, and delete on exit."""
        url = cloudinary.utils.cloudinary_url(storage_reference, resource_type="raw", type="authenticated", sign_url=True)[0]
        
        fd, temp_path = tempfile.mkstemp()
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        raise StorageError("stored document is missing or inaccessible")
                    
                    with os.fdopen(fd, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
            
            yield temp_path
        finally:
            # Clean up the temporary file
            try:
                os.remove(temp_path)
            except OSError:
                pass
