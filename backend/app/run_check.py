import asyncio
import os
from app.db.mongodb import connect_to_mongo, get_database

async def main():
    print("MONGODB_URL env:", os.environ.get("MONGODB_URL"))
    await connect_to_mongo()
    db = await get_database()
    docs = await db.documents.find().to_list(100)
    print(f"TOTAL_DOCUMENTS={len(docs)}")
    for d in docs:
        print(f"ID={d.get('_id')} | FILE={d.get('file_name')} | STATUS={d.get('status')} | STAGE={d.get('current_stage')} | PROGRESS={d.get('progress')}% | ERROR={d.get('processing_error')}")

if __name__ == "__main__":
    asyncio.run(main())
