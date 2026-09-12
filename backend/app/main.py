import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.facts import router as facts_router
from app.api.v1.health import router as health_router
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
from app.repositories.collections import (
    DocumentsRepository,
    StructuredFactsRepository,
    UsersCollectionRepository,
)
from app.services.auth import AuthError, AuthService
from app.services.documents import DocumentService
from app.services.facts import FactService
from app.services.health import HealthService
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
        DocumentsRepository(app.state.mongodb.database), app.state.storage, settings
    )
    app.state.fact_service = FactService(StructuredFactsRepository(app.state.mongodb.database))
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
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(facts_router, prefix="/api/v1")
