import asyncio
from app.core.config import get_settings
from app.db.mongo import MongoConnection
import app.tasks.documents as t
from app.storage.cloudinary_storage import CloudinaryStorage

async def main():
    settings = get_settings()
    conn = MongoConnection(settings)
    doc = await conn.database.documents.find_one({"file_name": "BANK PASSBOOK.pdf"})
    print(f"Doc ID: {doc['_id']} | User ID: {doc['user_id']} | Ref: {doc['storage_reference']}")
    
    storage = CloudinaryStorage(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
    )
    try:
        chk = await storage.checksum("BANK_PASSBOOK_rkgmkh.pdf")
        await conn.database.documents.update_one(
            {"_id": doc["_id"]},
            {"$set": {"storage_reference": "BANK_PASSBOOK_rkgmkh.pdf", "checksum": chk}}
        )
    except Exception as e:
        print("Update notice:", e)
        await conn.database.documents.update_one(
            {"_id": doc["_id"]},
            {"$set": {"storage_reference": "BANK_PASSBOOK_rkgmkh.pdf"}}
        )
    
    # 2. Run document processing pipeline
    print("Starting pipeline process...")
    await t._process(str(doc["_id"]), str(doc["user_id"]))
    print("PIPELINE PROCESS COMPLETED!")
    
    # 3. Check extracted facts for this user & doc
    facts = await conn.database.structured_facts.find({"source_document_id": str(doc["_id"])}).to_list(100)
    print(f"\nEXTRACTED FACTS COUNT FOR BANK PASSBOOK: {len(facts)}")
    for f in facts:
        print(f"  -> {f.get('concept')} = {repr(f.get('value'))} (conf: {f.get('confidence')})")

if __name__ == "__main__":
    asyncio.run(main())
