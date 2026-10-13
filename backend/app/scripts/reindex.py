"""Rebuild the configured Chroma collection from processed source documents.

Run from ``backend`` with ``python -m app.scripts.reindex``. Set
``CHROMADB_COLLECTION`` to the new collection name first. This command never
deletes or modifies a different collection.
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.db.chroma_client import ChromaClient
from app.db.mongo import MongoConnection
from app.processing.runner import context_from_settings, process_document


async def reindex() -> int:
    settings = get_settings()
    connection = MongoConnection(settings)
    database = connection.database
    vector_store = ChromaClient(settings)
    processed = 0
    failed = 0

    try:
        await vector_store.ensure_collection()
        context = context_from_settings(settings, database)
        cursor = database["documents"].find({"status": "processed"}, {"user_id": 1})
        async for record in cursor:
            document_id = str(record["_id"])
            await process_document(context, record["user_id"], document_id)
            updated = await database["documents"].find_one(
                {"_id": record["_id"], "user_id": record["user_id"]},
                {"status": 1, "index_status": 1},
            )
            if (
                updated
                and updated.get("status") == "processed"
                and updated.get("index_status") in {"indexed", "empty"}
            ):
                processed += 1
            else:
                failed += 1
                print(f"Reindex failed for document {document_id}")
    finally:
        connection.close()

    print(f"Reindexed {processed} documents; {failed} failed.")
    return 1 if failed else 0


def main() -> None:
    raise SystemExit(asyncio.run(reindex()))


if __name__ == "__main__":
    main()
