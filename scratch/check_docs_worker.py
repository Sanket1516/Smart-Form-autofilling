import asyncio
from app.core.config import get_settings
from app.db.mongo import MongoConnection

async def main():
    settings = get_settings()
    conn = MongoConnection(settings)
    docs = await conn.database.documents.find({"status": {"$ne": "deleted"}}).to_list(100)
    print(f"ACTIVE DOCS COUNT: {len(docs)}")
    for d in docs:
        print(f"ID: {d.get('document_id')} | Name: {d.get('file_name')} | User: {d.get('user_id')} | Status: {d.get('status')}")

if __name__ == "__main__":
    asyncio.run(main())
