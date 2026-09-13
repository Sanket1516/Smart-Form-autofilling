import asyncio
from app.db.mongodb import connect_to_mongo, get_database

async def main():
    await connect_to_mongo()
    db = await get_database()
    docs = await db.documents.find().to_list(100)
    print(f"TOTAL_DOCUMENTS={len(docs)}")
    for d in docs:
        print(f"ID={d.get('_id')} | FILE={d.get('filename')} | STATUS={d.get('status')} | STAGE={d.get('processing_stage')} | PROGRESS={d.get('processing_progress')}%")

if __name__ == "__main__":
    asyncio.run(main())
