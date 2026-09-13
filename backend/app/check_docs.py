import asyncio
from app.core.config import get_settings
from app.db.mongo import MongoConnection

async def main():
    settings = get_settings()
    conn = MongoConnection(settings)
    docs = await conn.database.documents.find({"status": {"$ne": "deleted"}}).to_list(100)
    print(f"Total active documents: {len(docs)}")
    for d in docs:
        print(f"ID: {d.get('document_id')} | File: {d.get('file_name')} | User: {d.get('user_id')} | Status: {d.get('status')}")
    
    user_id = "6aa5ac7a750ac7b4e8308688"
    user_facts = await conn.database.structured_facts.find({"user_id": user_id}).to_list(100)
    print(f"\nFACTS FOR USER {user_id} ({len(user_facts)} facts):")
    for f in user_facts:
        print(f"  - Concept: {f.get('concept')} | Value: {repr(f.get('value'))} | Conf: {f.get('confidence')} | DocID: {f.get('source_document_id')}")

if __name__ == "__main__":
    asyncio.run(main())
