import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.agents.semantic_classifier import SemanticClassifier
from app.agents.checkpoint import MongoAgentStore
from app.agents.graph import AutofillAgent
from app.agents.llm_provider import get_llm_provider
from app.agents.conflict_resolver import ConflictResolver
from app.api.v1.auth import router as auth_router
from app.api.v1.corrections import router as corrections_router
from app.api.v1.documents import router as documents_router
from app.api.v1.facts import router as facts_router
from app.api.v1.forms import router as forms_router
from app.api.v1.health import router as health_router
from app.api.v1.profile import router as profile_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.agent import router as agent_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.recommendations import router as recommendations_router
from app.core.api_errors import APIError
from app.core.config import get_settings
from app.core.exceptions import (
    application_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, request_logging_middleware
from app.db.chroma_client import ChromaClient
from app.db.mongo import MongoConnection
from app.db.mongo_database import MongoDatabase
from app.db.revocations import MongoRevocationStore
from app.ontology.loader import FieldOntology
from app.db.repositories.recommendations import RecommendationsRepository
from app.db.repositories.form_sessions import FormSessionsRepository
from app.repositories.collections import (
    CorrectionsRepository,
    DocumentsRepository,
    ProfilesRepository,
    StructuredFactsRepository,
    UsersCollectionRepository,
)
from app.retrieval.embeddings import DefaultEmbeddingProvider
from app.services.auth import AuthError, AuthService
from app.services.corrections import CorrectionsService
from app.services.documents import DocumentService
from app.services.facts import FactService
from app.services.health import HealthService
from app.services.profile import ProfileService
from app.services.retrieval import RAGRetrievalService
from app.storage.local import LocalFileStorage

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings
    app.state.mongodb = MongoConnection(settings)
    app.state.chromadb = ChromaClient(settings)
    app.state.mongo_database = MongoDatabase(app.state.mongodb)
    app.state.users_repository = UsersCollectionRepository(app.state.mongodb.database)
    app.state.revocations = MongoRevocationStore(app.state.mongodb.database)
    app.state.auth_service = AuthService(
        app.state.users_repository, app.state.revocations, settings
    )
    app.state.storage = LocalFileStorage(settings.storage_root)
    app.state.document_service = DocumentService(
        DocumentsRepository(app.state.mongodb.database),
        app.state.storage,
        settings,
        chroma_client=app.state.chromadb,
    )
    corrections_repo = CorrectionsRepository(app.state.mongodb.database)
    profiles_repo = ProfilesRepository(app.state.mongodb.database)
    structured_facts_repo = StructuredFactsRepository(app.state.mongodb.database)
    app.state.recommendations_repo = RecommendationsRepository(app.state.mongodb.database)
    app.state.form_sessions_repo = FormSessionsRepository(app.state.mongodb.database)

    app.state.corrections_service = CorrectionsService(corrections_repo)
    app.state.fact_service = FactService(
        structured_facts_repo, corrections_repository=corrections_repo
    )
    app.state.profile_service = ProfileService(profiles_repo, structured_facts_repo)
    app.state.field_ontology = FieldOntology()
    app.state.semantic_classifier = SemanticClassifier(ontology=app.state.field_ontology)
    app.state.embedding_provider = DefaultEmbeddingProvider(settings)
    app.state.retrieval_service = RAGRetrievalService(
        app.state.chromadb, app.state.embedding_provider
    )
    app.state.llm_provider = get_llm_provider(settings)
    app.state.conflict_resolver = ConflictResolver(
        confidence_threshold=settings.confidence_threshold,
        sensitive_concepts=settings.sensitive_concepts_list,
    )
    app.state.agent_store = MongoAgentStore(app.state.mongodb.database)
    app.state.agent_graph = AutofillAgent(
        semantic_classifier=app.state.semantic_classifier,
        fact_service=app.state.fact_service,
        retrieval_service=app.state.retrieval_service,
        llm_provider=app.state.llm_provider,
        conflict_resolver=app.state.conflict_resolver,
        recommendations_repo=app.state.recommendations_repo,
        max_evidence_chunks=settings.llm_max_evidence_chunks,
    )
    app.state.health_service = HealthService(app.state.mongodb, app.state.chromadb)
    try:
        await app.state.mongo_database.ensure_indexes()
    except Exception:
        logger.exception("mongodb_initialization_failed")
    try:
        await app.state.revocations.ensure_index()
    except Exception:
        logger.exception("auth_revocation_initialization_failed")
    try:
        await app.state.chromadb.ensure_collection()
    except Exception:
        logger.exception("chromadb_initialization_failed")
    try:
        await app.state.agent_store.ensure_indexes()
    except Exception:
        logger.exception("agent_store_initialization_failed")
    yield
    app.state.mongodb.close()


settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.middleware("http")(request_logging_middleware)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(APIError, application_error_handler)
app.add_exception_handler(AuthError, application_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(facts_router, prefix="/api/v1")
app.include_router(retrieval_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(corrections_router, prefix="/api/v1")
app.include_router(forms_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
