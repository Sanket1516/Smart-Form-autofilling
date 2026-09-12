"""TC-DB-08: user-scoped repositories cannot cross ownership boundaries."""

from typing import Any

import pytest
from app.repositories.collections import (
    DocumentsRepository,
    StructuredFactsRepository,
)


class FakeCursor:
    def __init__(self, documents: list[dict[str, Any]], query: dict[str, Any]) -> None:
        self.documents = documents
        self.query = query

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        return [
            document
            for document in self.documents
            if all(document.get(key) == value for key, value in self.query.items())
        ]


class FakeCollection:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = documents
        self.last_query: dict[str, Any] | None = None

    def find(self, query: dict[str, Any]) -> FakeCursor:
        self.last_query = query
        return FakeCursor(self.documents, query)


class FakeDatabase:
    def __init__(self, collections: dict[str, FakeCollection]) -> None:
        self.collections = collections

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections[name]


@pytest.mark.asyncio
async def test_documents_are_always_filtered_by_user_id() -> None:
    collection = FakeCollection(
        [
            {"_id": "doc-a", "user_id": "user-a", "file_name": "a.pdf"},
            {"_id": "doc-b", "user_id": "user-b", "file_name": "b.pdf"},
        ]
    )
    repository = DocumentsRepository(FakeDatabase({"documents": collection}))

    documents = await repository.list("user-a")

    assert [document["_id"] for document in documents] == ["doc-a"]
    assert collection.last_query == {"user_id": "user-a"}


@pytest.mark.asyncio
async def test_facts_are_always_filtered_by_user_id() -> None:
    collection = FakeCollection(
        [
            {"_id": "fact-a", "user_id": "user-a", "concept": "email"},
            {"_id": "fact-b", "user_id": "user-b", "concept": "email"},
        ]
    )
    repository = StructuredFactsRepository(FakeDatabase({"structured_facts": collection}))

    facts = await repository.list("user-a")

    assert [fact["_id"] for fact in facts] == ["fact-a"]
    assert collection.last_query == {"user_id": "user-a"}


@pytest.mark.asyncio
async def test_caller_filters_cannot_override_user_scope() -> None:
    collection = FakeCollection([{"_id": "doc-b", "user_id": "user-b", "file_name": "b.pdf"}])
    repository = DocumentsRepository(FakeDatabase({"documents": collection}))

    documents = await repository.list("user-a", {"user_id": "user-b"})

    assert documents == []
    assert collection.last_query == {"user_id": "user-a"}
