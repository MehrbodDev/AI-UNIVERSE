
from contextlib import asynccontextmanager
import math

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.core.http_client import create_http_client
from app.providers.catalog import list_provider_catalog
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.providers.lifecycle import (
    ProviderLifecycleInfo,
    ProviderLifecycleManager,
)
from app.providers.registry import registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application-scoped resources."""

    http_client = create_http_client(
        timeout=settings.api_timeout,
        allow_localhost=settings.environment == "development",
    )

    app.state.http_client = http_client

    try:
        registry.set_http_client(http_client)
        yield
    finally:
        registry.set_http_client(None)
        await http_client.aclose()


app = FastAPI(
    title="AI UNIVERSE API",
    description="Central backend for AI UNIVERSE",
    version="0.4.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


lifecycle_manager = ProviderLifecycleManager(registry)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    provider: str = "mock"


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str


def create_provider_error_response(
    error: ProviderError,
) -> JSONResponse:
    """Convert provider exceptions into safe, structured API errors."""

    if isinstance(error, ProviderAuthenticationError):
        status_code = 502
        error_code = "provider_authentication_failed"
        message = "Provider authentication failed."

    elif isinstance(error, ProviderRateLimitError):
        status_code = 429
        error_code = "provider_rate_limit"
        message = "Provider rate limit was reached."

    elif isinstance(error, ProviderTimeoutError):
        status_code = 504
        error_code = "provider_timeout"
        message = "Provider request timed out."

    elif isinstance(error, ProviderConnectionError):
        status_code = 503
        error_code = "provider_connection_failed"
        message = "Provider connection failed."

    elif isinstance(error, ProviderResponseError):
        status_code = 502
        error_code = "provider_invalid_response"
        message = "Provider returned an invalid response."

    else:
        status_code = 502
        error_code = "provider_error"
        message = "AI provider error."

    error_data = {
        "code": error_code,
        "message": message,
        "provider": error.provider,
        "retryable": error.retryable,
        "retry_after": error.retry_after,
    }

    headers = {}

    if error.retry_after is not None:
        headers["Retry-After"] = str(math.ceil(error.retry_after))

    return JSONResponse(
        status_code=status_code,
        content={"error": error_data},
        headers=headers,
    )


@app.get("/")
async def root():
    return {
        "project": "AI UNIVERSE",
        "status": "online",
        "version": "0.4.0",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "backend": "FastAPI",
        "message": "AI UNIVERSE backend is running",
    }


@app.get("/api/providers")
async def list_providers():
    return {
        "providers": registry.list_providers()
    }


@app.get("/api/providers/catalog")
async def get_provider_catalog():
    providers = list_provider_catalog()

    return {
        "total": len(providers),
        "providers": providers,
    }


@app.get("/api/providers/lifecycle")
async def get_provider_lifecycle_list():
    statuses = lifecycle_manager.list_statuses()

    return {
        "total": len(statuses),
        "providers": [
            status.model_dump(mode="json")
            for status in statuses
        ],
    }


@app.get(
    "/api/providers/{provider_id}/lifecycle",
    response_model=ProviderLifecycleInfo,
)
async def get_provider_lifecycle(provider_id: str):
    try:
        return lifecycle_manager.get_status(provider_id)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        provider = registry.get(request.provider)
        reply = await provider.chat(request.message)

        return {
            "reply": reply,
            "provider": provider.provider_name,
            "model": provider.model_name,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except ProviderError as error:
        return create_provider_error_response(error)

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI provider error.",
        ) from None
