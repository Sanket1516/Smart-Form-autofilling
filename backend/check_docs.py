import asyncio
from app.core.config import get_settings
from app.db.mongo import MongoConnection

async def main():
    settings = get_settings()
    conn = MongoConnection(settings)
    docs = await conn.database.documents.find({"status": {"$ne": "deleted"}}).to_list(100)
    print(f"Total documents: {len(docs)}")
    for d in docs:
        print(f"ID: {d.get('document_id')} | File: {d.get('file_name')} | User: {d.get('user_id')} | Status: {d.get('status')}")
    
    facts = await conn.database.structured_facts.find().to_list(200)
    print(f"Total structured_facts in DB: {len(facts)}")
    for f in facts[:20]:
        print(f"  - Fact: {f.get('concept')} = {repr(f.get('value'))} (doc: {f.get('source_document_id')})")

if __name__ == "__main__":
    asyncio.run(main())
