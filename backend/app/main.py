
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.providers.registry import registry
from app.providers.catalog import list_provider_catalog


app = FastAPI(
    title="AI UNIVERSE API",
    description="Central backend for AI UNIVERSE",
    version="0.4.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI provider error.",
        )
