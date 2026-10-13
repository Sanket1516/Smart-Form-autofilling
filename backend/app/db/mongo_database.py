"""MongoDB database initialization and index creation."""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

from app.db.indexes import MONGO_INDEXES
from app.db.mongo import MongoConnection

logger = logging.getLogger(__name__)


class MongoDatabase:
    """Expose the configured database and create the declared indexes."""

    def __init__(self, connection: MongoConnection) -> None:
        self._connection = connection

    @property
    def database(self) -> AsyncIOMotorDatabase:
        return self._connection.database

    async def ensure_indexes(self) -> None:
        """Create missing indexes one by one.

        An equivalent index that already exists under another name is kept as is,
        so upgrading never drops or rebuilds existing indexes.
        """
        for collection_name, indexes in MONGO_INDEXES.items():
            collection = self.database[collection_name]
            for index in indexes:
                try:
                    await collection.create_indexes([index])
                except OperationFailure as error:
                    logger.warning(
                        "mongodb_index_skipped",
                        extra={
                            "collection": collection_name,
                            "index": index.document.get("name"),
                            "reason": (
                                error.details.get("codeName") if error.details else str(error)
                            ),
                        },
                    )
        logger.info("mongodb_indexes_initialized", extra={"collections": list(MONGO_INDEXES)})
