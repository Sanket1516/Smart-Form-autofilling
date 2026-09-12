"""MongoDB database initialization and index creation."""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.indexes import MONGO_INDEXES
from app.db.mongo import MongoConnection

logger = logging.getLogger(__name__)


class MongoDatabase:
    """Expose the configured database and create the design indexes."""

    def __init__(self, connection: MongoConnection) -> None:
        self._connection = connection

    @property
    def database(self) -> AsyncIOMotorDatabase:
        return self._connection.database

    async def ensure_indexes(self) -> None:
        for collection_name, indexes in MONGO_INDEXES.items():
            await self.database[collection_name].create_indexes(indexes)
        logger.info("mongodb_indexes_initialized", extra={"collections": list(MONGO_INDEXES)})
