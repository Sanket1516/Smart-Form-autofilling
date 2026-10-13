"""MongoDB index definitions. Index creation is idempotent and non-destructive."""

from pymongo import ASCENDING, DESCENDING, IndexModel

MONGO_INDEXES: dict[str, list[IndexModel]] = {
    "users": [IndexModel([("email", ASCENDING)], unique=True, name="users_email_unique")],
    "documents": [
        IndexModel([("user_id", ASCENDING)], name="documents_user_id"),
        IndexModel(
            [("user_id", ASCENDING), ("status", ASCENDING)],
            name="documents_user_id_status",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("checksum", ASCENDING)],
            unique=True,
            name="documents_user_id_checksum_unique",
        ),
    ],
    "structured_facts": [
        IndexModel(
            [("user_id", ASCENDING), ("concept", ASCENDING)],
            name="structured_facts_user_id_concept",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("status", ASCENDING), ("concept", ASCENDING)],
            name="structured_facts_user_status_concept",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("source_document_id", ASCENDING)],
            name="structured_facts_user_source_document",
        ),
    ],
    "discovered_facts": [
        IndexModel(
            [("user_id", ASCENDING), ("source_document_id", ASCENDING)],
            name="discovered_facts_user_document",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("semantic_type", ASCENDING)],
            name="discovered_facts_user_semantic_type",
        ),
    ],
    "user_memories": [
        IndexModel(
            [("user_id", ASCENDING), ("updated_at", DESCENDING)],
            name="user_memories_user_updated",
        ),
    ],
    "recommendations": [
        IndexModel(
            [("user_id", ASCENDING), ("session_id", ASCENDING), ("field_id", ASCENDING)],
            name="recommendations_user_session_field",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("status", ASCENDING)],
            name="recommendations_user_status",
        ),
    ],
    "corrections": [
        IndexModel(
            [("user_id", ASCENDING), ("concept", ASCENDING)],
            name="corrections_user_id_concept",
        ),
    ],
    "processing_records": [
        IndexModel(
            [("user_id", ASCENDING), ("document_id", ASCENDING)],
            name="processing_records_user_document",
        ),
    ],
    "form_sessions": [
        IndexModel(
            [("user_id", ASCENDING), ("started_at", DESCENDING)],
            name="form_sessions_user_started",
        )
    ],
    "agent_runs": [
        IndexModel([("run_id", ASCENDING)], unique=True, name="agent_runs_run_id_unique"),
        IndexModel([("user_id", ASCENDING)], name="agent_runs_user_id"),
    ],
}
