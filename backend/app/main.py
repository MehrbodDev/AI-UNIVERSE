
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.core.http_client import create_http_client
from app.providers.catalog import list_provider_catalog
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
    )

    app.state.http_client = http_client

    try:
        yield
    finally:
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

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI provider error.",
        ) from None
