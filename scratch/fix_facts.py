import asyncio
from app.db.mongo import MongoConnection
from app.core.config import get_settings

async def main():
    settings = get_settings()
    conn = MongoConnection(settings)
    db = conn.database

    # Fix email OCR error
    r = await db['structured_facts'].update_many(
        {'concept': 'personal.email'},
        {'$set': {'value': 'sanketmali0909@gmail.com'}}
    )
    print('Fixed email:', r.modified_count)

    # Fix full name to Title Case first/last
    r2 = await db['structured_facts'].update_many(
        {'concept': 'personal.full_name', 'value': 'Mr. MALI SANKET KISHOR'},
        {'$set': {'value': 'Sanket Mali'}}
    )
    print('Fixed full_name:', r2.modified_count)

    # Fix bank name OCR garble
    r3 = await db['structured_facts'].update_many(
        {'concept': 'financial.bank_name'},
        {'$set': {'value': 'State Bank of India'}}
    )
    print('Fixed bank_name:', r3.modified_count)

    # Fix phone - keep just 10 digits
    phones = await db['structured_facts'].find({'concept': 'personal.phone'}).to_list(10)
    for p in phones:
        val = str(p.get('value', ''))
        cleaned = val.replace('+91', '').replace(' ', '').replace('-', '').strip()
        if cleaned.startswith('91') and len(cleaned) == 12:
            cleaned = cleaned[2:]
        if cleaned != val:
            await db['structured_facts'].update_one({'_id': p['_id']}, {'$set': {'value': cleaned}})
            print('Fixed phone:', val, '->', cleaned)

    # Also fix phone_number concept
    phones2 = await db['structured_facts'].find({'concept': 'phone_number'}).to_list(10)
    for p in phones2:
        val = str(p.get('value', ''))
        cleaned = val.replace('+91', '').replace(' ', '').replace('-', '').strip()
        if cleaned.startswith('91') and len(cleaned) == 12:
            cleaned = cleaned[2:]
        if cleaned != val:
            await db['structured_facts'].update_one({'_id': p['_id']}, {'$set': {'value': cleaned}})
            print('Fixed phone_number:', val, '->', cleaned)

    # Verify all
    for c in ['personal.email', 'personal.full_name', 'personal.phone', 'financial.bank_name', 'phone_number']:
        fs = await db['structured_facts'].find({'concept': c}).to_list(3)
        for f in fs:
            print('  {} -> {!r}'.format(c, f.get('value')))

    conn.close()

asyncio.run(main())
