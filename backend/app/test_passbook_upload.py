import asyncio
import os
from pathlib import Path
from app.core.config import get_settings
from app.db.mongo import MongoConnection
from app.storage.cloudinary_storage import CloudinaryStorage
import app.tasks.documents as t

async def main():
    settings = get_settings()
    conn = MongoConnection(settings)
    
    # Path to user's uploaded SBI Passbook PNG image
    img_path = Path(__file__).parent / "sample_passbook.png"
    if not os.path.exists(img_path):
        print("Image not found at path:", img_path)
        return
        
    with open(img_path, "rb") as f:
        content = f.read()
        
    storage = CloudinaryStorage(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
    )
    
    public_id, checksum = await storage.save("SBI_Passbook.png", [content])
    print(f"Uploaded to Cloudinary: public_id={public_id}, checksum={checksum}")
    
    import uuid
    user_id = f"test_user_{uuid.uuid4().hex[:6]}"
    doc_id = str(uuid.uuid4())[:24]
    
    doc_record = {
        "document_id": doc_id,
        "user_id": user_id,
        "file_name": "SBI_Passbook.png",
        "file_type": "image/png",
        "storage_reference": public_id,
        "checksum": checksum,
        "status": "uploaded",
        "current_stage": "upload",
        "progress": 0,
        "uploaded_at": "2026-09-13T14:00:00Z"
    }
    
    await conn.database.documents.insert_one(doc_record)
    print(f"Created document record in MongoDB: doc_id={doc_id}")
    
    print("Running document processing pipeline...")
    pipeline = t.DocumentPipeline(
        t.UniversalDocumentExtractor(t.PaddleOCRAdapter(language="en")),
        t.ProcessingRecordsRepository(conn.database),
        1,
        fact_extractor=t.DocumentOntologyExtractor(t.get_llm_provider(settings), t.FieldOntology()),
        fact_writer=t.StructuredFactsRepository(conn.database),
    )
    async with storage.get_local_path(public_id) as local_path:
        norm = await pipeline.run(user_id, doc_id, local_path, lambda v: asyncio.sleep(0), "SBI_Passbook.png")
    
    print("\n--- OCR EXTRACTED SPANS ---")
    for p in norm.pages:
        for s in p.spans:
            print("  - SPAN:", repr(s.text))
    
    # Fetch extracted facts
    facts = await conn.database.structured_facts.find({"source_document_id": doc_id}).to_list(100)
    print(f"\n================ EXTRACTED FACTS ({len(facts)}) ================")
    for f in facts:
        print(f"  -> CONCEPT: {f.get('concept'):<30} | VALUE: {repr(f.get('value')):<30} | CONF: {f.get('confidence')}")

if __name__ == "__main__":
    asyncio.run(main())
