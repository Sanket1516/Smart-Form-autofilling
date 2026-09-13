import asyncio
from app.db.mongo import MongoConnection
from app.core.config import get_settings

async def main():
    settings = get_settings()
    conn = MongoConnection(settings)
    db = conn.database

    user = await db['users'].find_one()
    if not user:
        print('No users found')
        return
    uid = str(user['_id'])
    print('User:', user.get('email'), 'uid:', uid)

    facts = await db['structured_facts'].find({'user_id': uid}).to_list(30)
    print('\n=== STRUCTURED FACTS ({}) ==='.format(len(facts)))
    for f in facts:
        print('  concept={} value={} conf={}'.format(f.get('concept'), repr(f.get('value')), f.get('confidence')))

    disc = await db['discovered_facts'].find({'user_id': uid}).to_list(50)
    print('\n=== DISCOVERED FACTS ({}) ==='.format(len(disc)))
    for f in disc:
        print('  semantic_type={} field={} value={} conf={}'.format(
            f.get('semantic_type'), f.get('field'), repr(f.get('value')), f.get('confidence')))

    conn.close()

asyncio.run(main())
