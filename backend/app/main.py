"""FastAPI application: dependency wiring, middleware and routers."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.agents.field_classifier import FieldClassifier
from app.agents.graph import FormFillGraph
from app.agents.llm_provider import get_llm_provider
from app.api.v1.agent import router as agent_router
from app.api.v1.auth import router as auth_router
from app.api.v1.corrections import router as corrections_router
from app.api.v1.documents import router as documents_router
from app.api.v1.exams import router as exams_router
from app.api.v1.facts import router as facts_router
from app.api.v1.forms import router as forms_router
from app.api.v1.health import router as health_router
from app.api.v1.profile import router as profile_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.reviews import router as reviews_router
from app.core.api_errors import APIError
from app.core.config import get_settings
from app.core.exceptions import (
    application_error_handler,
    http_exception_handler,
    rate_limit_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, request_logging_middleware
from app.core.rate_limit import limiter
from app.db.chroma_client import ChromaClient, VectorStoreError
from app.db.mongo import MongoConnection
from app.db.mongo_database import MongoDatabase
from app.db.repositories.form_sessions import FormSessionsRepository
from app.db.repositories.recommendations import RecommendationsRepository
from app.db.revocations import MongoRevocationStore
from app.exams.service import ExamService
from app.ontology.loader import FieldOntology
from app.processing.runner import ProcessingContext, build_storage, process_document
from app.repositories.collections import (
    CorrectionsRepository,
    DiscoveredFactsRepository,
    DocumentsRepository,
    ProcessingRecordsRepository,
    StructuredFactsRepository,
    UsersCollectionRepository,
)
from app.retrieval.embeddings import SentenceTransformerEmbeddings
from app.services.auth import AuthError, AuthService
from app.services.corrections import CorrectionsService
from app.services.document_qa import DocumentQAService
from app.services.documents import DocumentService
from app.services.facts import FactService
from app.services.form_filling import FormFillService
from app.services.health import HealthService
from app.services.profile import ProfileService
from app.services.retrieval import RAGAnswerService, RAGRetrievalService
from app.services.user_data import UserDataService
from app.services.user_memories import UserMemoryService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    state = app.state
    state.settings = settings
    state.mongodb = MongoConnection(settings)
    database = state.mongodb.database
    state.field_ontology = ontology = FieldOntology()
    state.llm_provider = llm = get_llm_provider(settings)
    state.embedding_provider = embeddings = SentenceTransformerEmbeddings(
        settings.embedding_model_name, settings.embedding_dimension
    )
    state.chromadb = vector_store = ChromaClient(settings)
    state.storage = storage = build_storage(settings)

    state.users_repository = UsersCollectionRepository(database)
    state.revocations = MongoRevocationStore(database)
    state.auth_service = AuthService(state.users_repository, state.revocations, settings)

    facts_repo = StructuredFactsRepository(database)
    corrections_repo = CorrectionsRepository(database)
    state.discovered_facts_repo = DiscoveredFactsRepository(database)
    state.recommendations_repo = RecommendationsRepository(database)
    state.form_sessions_repo = FormSessionsRepository(database)
    state.corrections_service = CorrectionsService(corrections_repo)
    state.fact_service = FactService(facts_repo, ontology, corrections_repo)
    state.profile_service = ProfileService(state.fact_service, ontology)
    state.exam_service = ExamService(state.fact_service, ontology)
    state.user_memory_service = UserMemoryService(database, vector_store, embeddings)
    state.retrieval_service = RAGRetrievalService(
        vector_store, embeddings, settings.rag_min_similarity
    )
    state.rag_answer_service = RAGAnswerService(state.retrieval_service, llm)
    state.user_data_service = UserDataService(database, storage, vector_store)
    state.document_qa_service = DocumentQAService(
        facts=state.fact_service,
        retrieval=state.retrieval_service,
        llm=llm,
        ontology=ontology,
        documents=DocumentsRepository(database),
        exam_service=state.exam_service,
    )

    processing_context = ProcessingContext(
        settings=settings,
        database=database,
        storage=storage,
        llm=llm,
        embeddings=embeddings,
        vector_store=vector_store,
        ontology=ontology,
    )
    background: set[asyncio.Task[None]] = set()

    def dispatch_inline(user_id: str, document_id: str) -> None:
        task = asyncio.create_task(process_document(processing_context, user_id, document_id))
        background.add(task)
        task.add_done_callback(background.discard)

    state.processing_tasks = background
    state.document_service = DocumentService(
        DocumentsRepository(database),
        storage,
        settings,
        facts=facts_repo,
        discovered=state.discovered_facts_repo,
        stages=ProcessingRecordsRepository(database),
        vector_store=vector_store,
        recommendations=state.recommendations_repo,
        dispatcher=dispatch_inline,
    )

    state.field_classifier = FieldClassifier(
        ontology, llm, settings.classifier_confidence_threshold
    )
    state.form_fill_graph = FormFillGraph(
        settings=settings,
        ontology=ontology,
        classifier=state.field_classifier,
        facts=state.fact_service,
        retrieval=state.retrieval_service,
        llm=llm,
        recommendations=state.recommendations_repo,
    )
    state.form_fill_service = FormFillService(
        sessions=state.form_sessions_repo,
        recommendations=state.recommendations_repo,
        graph=state.form_fill_graph,
        facts=state.fact_service,
        memories=state.user_memory_service,
        ontology=ontology,
    )
    state.health_service = HealthService(state.mongodb, vector_store, llm, embeddings)

    try:
        await MongoDatabase(state.mongodb).ensure_indexes()
        await state.revocations.ensure_index()
    except Exception:
        logger.error(
            "mongodb_initialization_failed: check MONGODB_URL; requests needing the database will fail"
        )
    try:
        await vector_store.ensure_collection()
    except VectorStoreError as error:
        logger.error("chromadb_initialization_failed", extra={"error": str(error)})
    logger.info(
        "application_started",
        extra={
            "llm_provider": llm.name,
            "processing_mode": settings.processing_mode,
            "storage_provider": settings.storage_provider,
        },
    )
    yield
    if background:
        await asyncio.wait(background, timeout=30)
    state.mongodb.close()


settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.state.limiter = limiter
app.middleware("http")(request_logging_middleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(APIError, application_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(AuthError, application_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)
for router in (
    health_router,
    auth_router,
    documents_router,
    facts_router,
    retrieval_router,
    profile_router,
    corrections_router,
    forms_router,
    agent_router,
    reviews_router,
    recommendations_router,
    exams_router,
):
    app.include_router(router, prefix="/api/v1")
