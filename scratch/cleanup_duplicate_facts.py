import pymongo

mongo_url = "mongodb://smart_form:replace_with_a_local_development_password@localhost:27017/smart_form_db?authSource=admin"
client = pymongo.MongoClient(mongo_url)
db = client["smart_form_db"]
col = db["structured_facts"]

SINGLETON_PREFIXES = (
    "personal.",
    "identity.",
    "contact.",
    "demographics.",
    "address.",
    "passport.",
    "visa.",
)

facts = list(col.find())
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
        col.delete_one({"_id": dup["_id"]})
        removed_count += 1

remaining = col.count_documents({})
print(f"Cleanup finished! Removed {removed_count} duplicate facts. Remaining total facts: {remaining}")
