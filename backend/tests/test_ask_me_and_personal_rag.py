"""Coverage for privacy-first Ask Me answers and personal-history RAG prompting."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from app.agents.prompts import build_rag_answer_prompt
from app.api.v1.forms import (
    _concept_from_label,
    _is_narrative_field,
    _normalize_answer,
    submit_ask_me_answers,
)
from app.api.v1.retrieval import answer_from_rag
from app.api.v1.reviews import submit_decision
from app.schemas.form_sessions import AskMeAnswersRequest
from app.schemas.retrieval import (
    RAGAnswerRequest,
    RAGChunkMetadata,
    RAGRetrievalData,
    RAGSearchResult,
)
from app.schemas.reviews import ReviewDecisionRequest
from app.services.user_memories import UserMemoryService


class FakeRecommendationsCollection:
    def __init__(self) -> None:
        self.items = [
            {
                "_id": "rec-name",
                "user_id": "user-1",
                "session_id": "session-1",
                "field_id": "name",
                "field_label": "Applicant Name",
                "concept": "unknown",
                "required": True,
                "input_type": "text",
                "status": "missing_information",
            },
            {
                "_id": "rec-income",
                "user_id": "user-1",
                "session_id": "session-1",
                "field_id": "income",
                "field_label": "Annual Income",
                "concept": "unknown",
                "required": True,
                "input_type": "number",
                "status": "missing_information",
            },
        ]

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        return next(
            (item for item in self.items if all(item.get(k) == v for k, v in query.items())), None
        )

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        item = await self.find_one(query)
        if item:
            item.update(update.get("$set", {}))

    async def count_documents(self, query: dict[str, Any]) -> int:
        return sum(1 for item in self.items if all(item.get(k) == v for k, v in query.items()))


class FakeFormSessionsRepository:
    async def get_session(self, user_id: str, session_id: str) -> dict[str, str] | None:
        return {"_id": session_id} if (user_id, session_id) == ("user-1", "session-1") else None

    async def update_session(self, user_id: str, session_id: str, updates: dict[str, Any]) -> bool:
        self.updates = updates
        return True


class FakeUserMemoryService:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str, str, Any]] = []

    async def save(self, user_id: str, label: str, concept: str, value: Any) -> None:
        self.saved.append((user_id, label, concept, value))


class FakeProfileService:
    def __init__(self) -> None:
        self.updates: list[Any] = []

    async def update(self, user_id: str, body: Any) -> None:
        self.updates.append(body)


def test_personal_story_fields_are_treated_as_narrative() -> None:
    assert _is_narrative_field("Tell us about yourself")
    assert _is_narrative_field("Past experience", "Describe your role")
    assert _concept_from_label("Applicant Name") == "personal.full_name"
    assert _concept_from_label("Family Annual Income") == "personal.annual_income"
    assert _concept_from_label("Email Address", "personal.email") == "contact.email"


def test_ask_me_answers_are_normalized_into_existing_profile_concepts() -> None:
    assert _normalize_answer("15/08/2007", "personal.date_of_birth", "text") == "2007-08-15"
    assert _normalize_answer("₹ 4,50,000", "personal.annual_income", "number") == 450000


def test_rag_narrative_prompt_is_grounded_and_treats_question_as_untrusted() -> None:
    prompt = build_rag_answer_prompt(
        "Tell us about your past experience",
        [{"text": "Worked as a student intern on a Python project.", "similarity": 0.91}],
    )
    assert "concise first-person answer" in prompt
    assert "<UNTRUSTED_FORM_QUESTION>" in prompt
    assert "Do not invent facts" in prompt


@pytest.mark.asyncio
async def test_ask_me_answers_only_persist_after_explicit_opt_in() -> None:
    recommendations = FakeRecommendationsCollection()
    memories = FakeUserMemoryService()
    profiles = FakeProfileService()
    sessions = FakeFormSessionsRepository()
    state = SimpleNamespace(
        recommendations_repo=SimpleNamespace(collection=recommendations),
        form_sessions_repo=sessions,
        user_memory_service=memories,
        profile_service=profiles,
    )
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    body = AskMeAnswersRequest(
        answers=[
            {"field_id": "name", "value": "Sanket Mali", "save_for_future": False},
            {"field_id": "income", "value": "₹ 4,50,000", "save_for_future": True},
        ]
    )

    response = await submit_ask_me_answers(
        "session-1", body, request, SimpleNamespace(user_id="user-1")
    )

    assert response.data is not None
    assert response.data.status == "ready"
    assert response.data.saved_count == 1
    assert recommendations.items[0]["recommended_value"] == "Sanket Mali"
    assert recommendations.items[0]["status"] == "READY_TO_FILL"
    assert len(memories.saved) == 1
    assert memories.saved[0][2:] == ("personal.annual_income", 450000)
    assert profiles.updates[0].personal == {"annual_income": 450000}


@pytest.mark.asyncio
async def test_personal_rag_answer_uses_authenticated_user_evidence() -> None:
    class FakeRetrieval:
        def __init__(self) -> None:
            self.user_id = ""

        async def search(self, user_id: str, request: Any) -> RAGRetrievalData:
            self.user_id = user_id
            return RAGRetrievalData(
                results=[
                    RAGSearchResult(
                        chunk_id="chunk-1",
                        text="Completed a college project using Python and React.",
                        similarity=0.93,
                        metadata=RAGChunkMetadata(
                            document_id="resume-1", page_number=2, language="en"
                        ),
                    )
                ]
            )

    class FakeLLM:
        def complete(self, prompt: str) -> str:
            assert "Tell us about your experience" in prompt
            return (
                '{"answer":"I completed a college project using Python and React.",'
                '"confidence":0.91}'
            )

    retrieval = FakeRetrieval()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(llm_provider=FakeLLM())))
    response = await answer_from_rag(
        RAGAnswerRequest(question="Tell us about your experience"),
        request,
        SimpleNamespace(user_id="user-1"),
        retrieval,
    )

    assert retrieval.user_id == "user-1"
    assert response.data is not None
    assert response.data.answer.startswith("I completed")
    assert response.data.sources[0].document_id == "resume-1"


@pytest.mark.asyncio
async def test_review_approval_persists_only_with_explicit_consent() -> None:
    class FakeReviewRepository:
        def __init__(self) -> None:
            self.record = {
                "_id": "review-1",
                "user_id": "user-1",
                "session_id": "session-1",
                "field_id": "about",
                "field_label": "Tell us about yourself",
                "concept": "profile.narrative",
                "recommended_value": "I study engineering.",
                "status": "pending_review",
                "source_fact_ids": [],
            }

        async def get_recommendation(self, user_id: str, review_id: str) -> dict[str, Any] | None:
            return (
                self.record
                if user_id == self.record["user_id"] and review_id == self.record["_id"]
                else None
            )

        async def update_status(
            self, user_id: str, review_id: str, status: str, value: str | None = None
        ) -> bool:
            self.record["status"] = status
            if value is not None:
                self.record["recommended_value"] = value
            return True

    class FakeFactRepository:
        def __init__(self) -> None:
            self.created: list[Any] = []

        async def create(self, user_id: str, document: Any) -> None:
            self.created.append(document)

    reviews = FakeReviewRepository()
    facts = FakeFactRepository()
    memories = FakeUserMemoryService()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                recommendations_repo=reviews,
                fact_service=SimpleNamespace(repository=facts),
                user_memory_service=memories,
            )
        )
    )
    user = SimpleNamespace(user_id="user-1")

    await submit_decision("review-1", ReviewDecisionRequest(decision="confirm"), request, user)
    assert not facts.created
    assert not memories.saved

    reviews.record["status"] = "pending_review"
    await submit_decision(
        "review-1",
        ReviewDecisionRequest(decision="confirm", save_for_future=True),
        request,
        user,
    )
    assert len(facts.created) == 1
    assert len(memories.saved) == 1


@pytest.mark.asyncio
async def test_user_memory_is_embedded_and_user_scoped_for_future_rag() -> None:
    class FakeCursor:
        def __init__(self, items: list[dict[str, Any]]) -> None:
            self.items = items

        def sort(self, *_args: Any) -> FakeCursor:
            return self

        def __aiter__(self):
            self.index = 0
            return self

        async def __anext__(self) -> dict[str, Any]:
            if self.index >= len(self.items):
                raise StopAsyncIteration
            item = self.items[self.index]
            self.index += 1
            return item

    class FakeCollection:
        def __init__(self) -> None:
            self.items: list[dict[str, Any]] = []

        def find(self, query: dict[str, Any], *_args: Any) -> FakeCursor:
            return FakeCursor(
                [item for item in self.items if all(item.get(k) == v for k, v in query.items())]
            )

        async def insert_one(self, item: dict[str, Any]) -> None:
            self.items.append(item)

        async def delete_one(self, query: dict[str, Any]) -> Any:
            before = len(self.items)
            self.items = [
                item for item in self.items if not all(item.get(k) == v for k, v in query.items())
            ]
            return SimpleNamespace(deleted_count=before - len(self.items))

        async def delete_many(self, query: dict[str, Any]) -> None:
            self.items = [
                item for item in self.items if not all(item.get(k) == v for k, v in query.items())
            ]

    class FakeDatabase:
        def __init__(self) -> None:
            self.collection = FakeCollection()

        def __getitem__(self, _name: str) -> FakeCollection:
            return self.collection

    class FakeChroma:
        def __init__(self) -> None:
            self.chunks: list[Any] = []
            self.deleted: list[tuple[str, str]] = []

        async def add_chunks(self, chunks: list[Any], _embeddings: list[list[float]]) -> None:
            self.chunks.extend(chunks)

        async def delete_document_chunks(self, user_id: str, document_id: str) -> None:
            self.deleted.append((user_id, document_id))

    class FakeEmbeddings:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0] for _ in texts]

    database = FakeDatabase()
    chroma = FakeChroma()
    memories = UserMemoryService(database, chroma, FakeEmbeddings())  # type: ignore[arg-type]
    saved = await memories.save(
        "user-1", "Past experience", "experience.summary", "Student internship in robotics"
    )

    assert saved["value"] == "Student internship in robotics"
    assert chroma.chunks[0].metadata["user_id"] == "user-1"
    assert "Past experience" in chroma.chunks[0].text
    assert len(await memories.list("user-1")) == 1
    assert await memories.delete("user-1", saved["memory_id"])
    assert chroma.deleted == [("user-1", saved["memory_id"])]
