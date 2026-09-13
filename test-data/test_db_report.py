import asyncio
import sys
import os
import shutil
from uuid import uuid4
from datetime import datetime, UTC

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))
from app.core.config import get_settings
from app.db.mongo import MongoConnection
from app.db.chroma_client import ChromaClient
from app.repositories.collections import DocumentsRepository, StructuredFactsRepository
from app.storage.local import LocalFileStorage
from app.tasks.documents import _process

from app.models.documents import DocumentRecord

async def main():
    settings = get_settings()
    connection = MongoConnection(settings)
    docs_repo = DocumentsRepository(connection.database)
    facts_repo = StructuredFactsRepository(connection.database)
    chroma = ChromaClient(settings)
    
    user_id = f"test-user-{uuid4()}"
    document_id = f"test-doc-{uuid4()}"
    file_path = "test-data/sanket_mali.pdf"
    
    storage = LocalFileStorage(settings.storage_root)
    storage_ref = f"{user_id}/{document_id}.pdf"
    os.makedirs(os.path.join(settings.storage_root, user_id), exist_ok=True)
    shutil.copy(file_path, os.path.join(settings.storage_root, storage_ref))
    
    doc = DocumentRecord(
        user_id=user_id,
        file_name="sanket_mali.pdf",
        file_type="application/pdf",
        file_size=os.path.getsize(file_path),
        document_type="resume",
        storage_reference=storage_ref,
        checksum=await storage.checksum(storage_ref),
        status="uploaded",
        uploaded_at=datetime.now(UTC),
        progress=0,
    )
    payload = await docs_repo.create(user_id, doc)
    document_id = str(payload["_id"])
    
    print(f"Processing document {document_id}...")
    await _process(document_id, user_id)
    
    print("Done. Fetching from MongoDB facts...")
    facts = await facts_repo.list_for_document(user_id, document_id)
    print(f"\n--- Extracted Facts (MongoDB) ---")
    extracted = set()
    for f in facts:
        print(f"[{f['concept']}] {f['value']} (Conf: {f['confidence']})")
        extracted.add(f['concept'])
        
    print(f"\nExtracted {len(facts)} facts covering {len(extracted)} concepts.")
        
    print("\n--- Chunks (ChromaDB) ---")
    try:
        collection = chroma._client.get_collection(settings.chromadb_collection)
        results = collection.get(where={"document_id": document_id})
        print(f"Total Chunks in ChromaDB: {len(results['ids'])}")
        for i in range(min(5, len(results['ids']))):
            print(f"Chunk ID: {results['ids'][i]}")
            print(f"Text snippet: {results['documents'][i][:100]}...\n")
    except Exception as e:
        print(f"Could not read from ChromaDB directly: {e}")
        
    connection.close()

if __name__ == "__main__":
    asyncio.run(main())
