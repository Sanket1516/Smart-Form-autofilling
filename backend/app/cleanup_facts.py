import asyncio
from app.db.mongodb import connect_to_mongo, get_database

SINGLETON_PREFIXES = (
    "personal.",
    "identity.",
    "contact.",
    "demographics.",
    "address.",
    "passport.",
    "visa.",
)

async def main():
    await connect_to_mongo()
    db = await get_database()
    col = db["structured_facts"]

    facts = await col.find().to_list(5000)
    print(f"Total facts in DB before cleanup: {len(facts)}")

    grouped = {}
    for f in facts:
        user_id = str(f.get("user_id", ""))
        c = str(f.get("concept", ""))
        v = str(f.get("value", "") or "").strip().lower()

        if any(c.startswith(prefix) for prefix in SINGLETON_PREFIXES):
            key = f"{user_id}:singleton:{c}"
        else:
            key = f"{user_id}:multi:{c}:{v}"

        if key not in grouped:
            grouped[key] = []
        grouped[key].append(f)

    removed_count = 0
    for key, item_list in grouped.items():
        if len(item_list) <= 1:
            continue

        def sort_key(item):
            conf = float(item.get("confidence") or 0.0)
            confirmed = 1 if item.get("is_user_confirmed") else 0
            updated = str(item.get("updated_at") or "")
            return (confirmed, conf, updated)

        sorted_list = sorted(item_list, key=sort_key, reverse=True)
        winner = sorted_list[0]
        duplicates_to_delete = sorted_list[1:]

        for dup in duplicates_to_delete:
            await col.delete_one({"_id": dup["_id"]})
            removed_count += 1

    remaining = await col.count_documents({})
    print(f"Cleanup finished! Removed {removed_count} duplicate facts. Remaining total facts: {remaining}")

if __name__ == "__main__":
    asyncio.run(main())
