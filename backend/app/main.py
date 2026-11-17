
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.providers.ollama_provider import chat_with_ollama


app = FastAPI(
    title="AI UNIVERSE API",
    description="Central backend for AI UNIVERSE",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    model: str


@app.get("/")
async def root():
    return {
        "project": "AI UNIVERSE",
        "status": "online",
        "version": "0.2.0",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "backend": "FastAPI",
        "message": "AI UNIVERSE backend is running",
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = await chat_with_ollama(request.message)

        return {
            "reply": reply,
            "model": "qwen3:4b",
        }

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"AI provider error: {str(error)}",
        )
