from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core.apis.api import api_router
from core.config import settings
from core.database import close_mongo_connection, create_indexes, connect_to_mongo
from core.middleware import RequestBodyLimitMiddleware, RequestSecurityMiddleware

logger = logging.getLogger("whitfield.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_mongo()
    await create_indexes()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="Whitfield WMS API",
    version="0.1.0",
    description="Transactional inventory APIs for a multi-seller 3PL warehouse.",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(RequestBodyLimitMiddleware, max_bytes=settings.max_request_body_bytes)
app.add_middleware(RequestSecurityMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1_000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Actor-Id", "X-Organization-Id", "X-Request-Id"],
    expose_headers=["X-Request-Id"],
    max_age=600,
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, error: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": [{"field": ".".join(str(part) for part in item["loc"] if part != "body"), "message": item["msg"]} for item in error.errors()], "request_id": getattr(request.state, "request_id", None)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, error: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled API exception request_id=%s", request_id, exc_info=error)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
