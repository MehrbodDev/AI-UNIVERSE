# AI UNIVERSE

**Multi-AI Command Center**

AI UNIVERSE is a multi-provider AI workspace in active development. Its goal is to bring supported cloud AI services and AI workflows into one unified interface.

> **Current status:** The dashboard and initial provider architecture exist. The backend currently runs a mock provider only. No real AI provider integration is enabled.

## Project goals

- A unified workspace for supported AI services
- Compare model responses through an AI Arena
- Research, learning, coding, and knowledge workflows
- Provider-independent backend architecture
- Account-level usage limits, cost controls, and privacy safeguards

## Planned provider catalog

The catalog currently describes these 11 providers as planned entries:

1. OpenAI — ChatGPT
2. Google — Gemini
3. xAI — Grok
4. Microsoft — Copilot
5. DeepSeek
6. Alibaba — Qwen
7. Anthropic — Claude
8. Z.ai — GLM
9. Moonshot AI — Kimi
10. Mistral AI
11. Perplexity

These entries are **not active integrations**. API availability, official terms, licensing, age requirements, regional availability, and technical feasibility must be reviewed before enabling any provider. Some services may only be usable through their official external workspaces.

## Current implementation

### Backend

- FastAPI application
- Health endpoint: `GET /api/health`
- Provider listing: `GET /api/providers`
- Provider catalog: `GET /api/providers/catalog`
- Chat endpoint: `POST /api/chat`
- `BaseProvider` abstract provider contract
- `ProviderRegistry` for provider registration and lookup
- `MockProvider` for local architecture testing
- Pydantic provider schemas
- Automated provider catalog tests

The chat endpoint currently uses the mock provider. It does not call OpenAI, Gemini, or any other external AI service.

### Frontend

- Next.js App Router
- React and TypeScript
- Tailwind CSS
- Dashboard interface
- Backend health check against `http://127.0.0.1:8010/api/health`

The AI workspace modules are interface placeholders unless explicitly stated otherwise. A visible module card does not mean its underlying feature is implemented.

## Technology stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, Pydantic, Uvicorn
- **Testing:** pytest
- **Tooling:** Git, GitHub, Visual Studio Code

## Repository structure

```text
AI-UNIVERSE/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── catalog.py
│   │   │   ├── mock_provider.py
│   │   │   └── registry.py
│   │   └── schemas/
│   │       └── provider.py
│   ├── tests/
│   │   └── test_providers/
│   │       └── test_catalog.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   └── app/
│   │       ├── globals.css
│   │       ├── icon.svg
│   │       ├── layout.tsx
│   │       └── page.tsx
│   ├── package.json
│   ├── package-lock.json
│   └── next.config.ts
├── .gitignore
└── README.md
```

## Run locally

### Backend

Open PowerShell:

```powershell
cd "$HOME\AI-UNIVERSE\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Backend health: `http://127.0.0.1:8010/api/health`

Interactive API documentation: `http://127.0.0.1:8010/docs`

### Frontend

Open a second terminal:

```powershell
cd "$HOME\AI-UNIVERSE\frontend"
npm ci
npm run dev
```

Frontend: `http://localhost:3000`

## Tests and quality checks

Backend tests:

```powershell
cd "$HOME\AI-UNIVERSE\backend"
.\.venv\Scripts\python.exe -m pytest
```

Frontend checks:

```powershell
cd "$HOME\AI-UNIVERSE\frontend"
npm run lint
npm run build
```

## Security principles

- Keep provider API keys on the backend only.
- Never commit `.env` files, credentials, or tokens.
- Do not expose secrets in frontend code or browser responses.
- Integrate providers only through authorized official APIs or permitted official workspaces.
- Respect provider terms, age requirements, regional restrictions, and licensing.
- Apply authentication, per-user quotas, rate limits, and cost controls before public production use.
- Do not silently switch users to paid providers or paid endpoints.
- Do not depend on local model runtimes or user GPUs.

## Development status

Implemented: initial frontend dashboard, backend health endpoint, provider abstraction, provider registry, mock provider, provider catalog metadata, and catalog tests.

Not yet implemented: real provider API integrations, production authentication, user-specific quotas, persistent chat history, model routing, multi-model orchestration, and production deployment.

## Project

- **Name:** AI UNIVERSE
- **Type:** Multi-AI platform
- **Status:** Active development
- **Repository:** https://github.com/MehrbodDev/AI-UNIVERSE