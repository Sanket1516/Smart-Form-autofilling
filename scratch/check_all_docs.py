import pymongo

mongo_url = "mongodb://smart_form:local_development_only@localhost:27017/smart_form_db?authSource=admin"
client = pymongo.MongoClient(mongo_url)
db = client["smart_form_db"]
docs = list(db["documents"].find())

print(f"Total Documents in DB: {len(docs)}")
for d in docs:
    print(f"ID: {d.get('_id')} | File: {d.get('file_name')} | Status: {d.get('status')} | Stage: {d.get('current_stage')} | Progress: {d.get('progress')}% | Error: {d.get('processing_error')}")
