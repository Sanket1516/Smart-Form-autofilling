"""MongoDB index definitions from DATABASE_DESIGN section 25."""

from pymongo import ASCENDING, IndexModel

MONGO_INDEXES: dict[str, list[IndexModel]] = {
    "users": [IndexModel([("email", ASCENDING)], unique=True, name="users_email_unique")],
    "profiles": [IndexModel([("user_id", ASCENDING)], name="profiles_user_id")],
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
            [
                ("user_id", ASCENDING),
                ("concept", ASCENDING),
                ("is_user_confirmed", ASCENDING),
            ],
            name="structured_facts_user_id_concept_confirmed",
        ),
        IndexModel([("source_document_id", ASCENDING)], name="structured_facts_source_document"),
    ],
    "recommendations": [
        IndexModel(
            [("user_id", ASCENDING), ("session_id", ASCENDING)],
            name="recommendations_user_id_session",
        ),
        IndexModel(
            [("session_id", ASCENDING), ("field_id", ASCENDING)],
            name="recommendations_session_field",
        ),
    ],
    "corrections": [
        IndexModel(
            [("user_id", ASCENDING), ("concept", ASCENDING)],
            name="corrections_user_id_concept",
        ),
        IndexModel([("session_id", ASCENDING)], name="corrections_session"),
    ],
    "feedback": [
        IndexModel(
            [("user_id", ASCENDING), ("created_at", ASCENDING)],
            name="feedback_user_id_created",
        )
    ],
    "processing_records": [
        IndexModel([("document_id", ASCENDING)], name="processing_records_document"),
        IndexModel(
            [("user_id", ASCENDING), ("status", ASCENDING)],
            name="processing_records_user_id_status",
        ),
    ],
    "form_sessions": [
        IndexModel(
            [("user_id", ASCENDING), ("started_at", ASCENDING)],
            name="form_sessions_user_id_started",
        )
    ],
}
