import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def reset_stuck_docs():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['smart_form_db']
    res = await db['documents'].update_many(
        {'status': 'processing'},
        {'$set': {'status': 'uploaded', 'current_stage': None, 'progress': 0}}
    )
    print(f'Successfully reset {res.modified_count} stuck document records.')

asyncio.run(reset_stuck_docs())
