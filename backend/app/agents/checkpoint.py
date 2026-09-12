"""MongoDB state storage adapter for the agentic workflow."""

import logging
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

class MongoAgentStore:
    """Stores and retrieves agent run states in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str = "agent_runs") -> None:
        self.collection = db[collection_name]

    async def ensure_indexes(self) -> None:
        """Create necessary indexes for agent runs."""
        await self.collection.create_index("run_id", unique=True)
        await self.collection.create_index("user_id")

    async def create_run(self, run_id: str, state: AgentState) -> None:
        """Creates a new agent run record."""
        doc = {
            "run_id": run_id,
            "user_id": state.get("user_id"),
            "status": state.get("status", "started"),
            "state": state,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await self.collection.insert_one(doc)

    async def update_run(self, run_id: str, state: AgentState) -> None:
        """Updates an existing agent run with the latest state."""
        await self.collection.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "state": state,
                    "status": state.get("status", "started"),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieves a run by ID."""
        doc = await self.collection.find_one({"run_id": run_id})
        if doc:
            # Convert ObjectId to string if we need to serialize it, though _id is not requested
            doc["_id"] = str(doc["_id"])
        return doc
