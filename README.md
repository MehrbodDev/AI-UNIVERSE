# AI UNIVERSE

**Multi-AI Command Center**

AI UNIVERSE is a multi-provider AI workspace in active development. Its goal is to bring supported AI services and AI workflows into one unified interface.

> **Current status:** The project includes a working multi-provider orchestration endpoint, a frontend multi-provider chat interface, a Mock provider, and an OpenAI adapter implementation. The OpenAI integration is not yet approved for production activation. The current active provider registry contains Mock only.

## Project goals

- A unified workspace for supported AI services
- Compare model responses through an AI Arena
- Research, learning, coding, and knowledge workflows
- Provider-independent backend architecture
- Account-level usage limits, cost controls, and privacy safeguards
- Secure and maintainable communication with external provider APIs

## Provider catalog

The project tracks these 11 planned providers:

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

These catalog entries do not automatically represent active integrations.

Each provider must pass the required technical, API availability, regional, licensing, age-policy, and authorization checks before activation.

### Current provider status

| Provider           | Implementation                  | Runtime status            |
| ------------------ | ------------------------------- | ------------------------- |
| Mock               | Implemented                     | Registered                |
| OpenAI             | Adapter and factory implemented | Pending activation review |
| Other 10 providers | Planned                         | Not implemented           |

Only one real provider is currently under implementation review: OpenAI.

## Current implementation

### Backend

The backend is built with FastAPI and includes:

- `GET /api/health` — Backend health check
- `GET /api/providers` — Registered providers
- `GET /api/providers/catalog` — Provider catalog
- `GET /api/providers/lifecycle` — Provider lifecycle information
- `POST /api/chat` — Single-provider chat
- `POST /api/chat/multi` — Concurrent multi-provider chat

The provider architecture includes:

- Provider abstraction through `BaseProvider`
- Provider registration and lookup through `ProviderRegistry`
- Provider creation through `ProviderFactory`
- Provider lifecycle validation
- Pydantic-based provider schemas
- Independent result and error handling for multi-provider requests
- Shared asynchronous HTTP client infrastructure
- Centralized network security configuration and validation

### Multi-provider orchestration

The multi-chat endpoint supports requests to between 2 and 5 providers.

Example request:

```json
{
  "message": "What is artificial intelligence?",
  "providers": ["mock", "openai"]
}
```

The backend:

- Runs provider requests concurrently
- Keeps each provider result independent
- Reports successful and failed requests separately
- Returns provider and model information
- Provides structured error information
- Prevents one provider failure from hiding other provider results

A provider must be registered and available at runtime to produce a successful response.

The existence of a provider in the catalog does not mean that it is connected.

### OpenAI integration

The project contains an OpenAI adapter based on the official Responses API.

Implementation includes:

- Configurable API key
- Configurable model
- Configurable timeout
- Optional base URL
- Shared HTTP client injection
- Response parsing and validation
- Provider-specific error handling
- No API key exposure through frontend configuration

The adapter implementation is present, but the provider remains subject to lifecycle, policy, authorization, and integration verification.

The current provider registry does not automatically register OpenAI merely because its environment configuration is present.

### HTTP and network security

The backend includes shared infrastructure for outbound HTTP communication.

The implementation focuses on:

- Centralized HTTP client configuration
- TLS certificate verification
- Hostname validation
- Timeout configuration validation
- Consistent provider transport behavior
- HTTP client lifecycle management
- Automated security and transport integration tests

Dependency upgrades should be accompanied by compatibility and security test runs.

## Frontend

The frontend uses:

- Next.js App Router
- React
- TypeScript
- Tailwind CSS

The chat interface includes:

- Provider catalog loading
- Provider lifecycle information
- Provider selection
- Multi-provider request submission
- Independent provider result display
- Success and failure status display
- Structured error information
- Chat turn history
- Chat clearing

The frontend communicates with the backend API.

A provider shown in the interface is not necessarily active or capable of producing a real response.

## Technology stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, Pydantic, HTTPX, Uvicorn
- **HTTP transport:** HTTPX and HTTPCore
- **Testing:** pytest
- **Tooling:** Git, GitHub, Visual Studio Code

## Repository structure

```text
AI-UNIVERSE/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── http_client.py
│   │   │   └── network_security.py
│   │   ├── config/
│   │   ├── providers/
│   │   │   └── adapters/
│   │   ├── schemas/
│   │   └── main.py
│   ├── tests/
│   │   ├── test_core/
│   │   ├── test_api/
│   │   └── test_providers/
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   └── app/
│   ├── package.json
│   ├── package-lock.json
│   └── next.config.ts
├── .gitattributes
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

Backend health:

`http://127.0.0.1:8010/api/health`

Interactive API documentation:

`http://127.0.0.1:8010/docs`

### Frontend

Open a second terminal:

```powershell
cd "$HOME\AI-UNIVERSE\frontend"
npm ci
npm run dev
```

Frontend:

`http://localhost:3000`

## Environment configuration

Provider settings are loaded from `backend/.env`.

OpenAI configuration uses these variable names:

```dotenv
AI_UNIVERSE_OPENAI_ENABLED=false
AI_UNIVERSE_OPENAI_API_KEY=
AI_UNIVERSE_OPENAI_MODEL=
AI_UNIVERSE_OPENAI_TIMEOUT=30
```

The values above are examples, not active credentials.

Important:

- Never commit `.env` files.
- Never put API keys in frontend code.
- Never paste API keys into source files or public issue trackers.
- Only use credentials with valid authorization for the project.
- Do not activate a provider until its required checks have passed.

## Tests and quality checks

### Backend tests

```powershell
cd "$HOME\AI-UNIVERSE\backend"
.\.venv\Scripts\python.exe -m pytest
```

### Backend dependency validation

```powershell
cd "$HOME\AI-UNIVERSE\backend"
.\.venv\Scripts\python.exe -m pip check
```

### Frontend checks

```powershell
cd "$HOME\AI-UNIVERSE\frontend"
npx tsc --noEmit
npm run lint
npm run build
```

## Security principles

- Keep provider API keys on the backend only.
- Never commit `.env` files, credentials, or tokens.
- Do not expose secrets in frontend code or browser responses.
- Verify TLS certificates for external HTTPS connections.
- Use explicit and validated timeout settings for outbound requests.
- Manage shared HTTP clients through their intended application lifecycle.
- Integrate providers only through authorized official APIs.
- Respect provider terms, age requirements, regional restrictions, and licensing.
- Apply authentication, per-user quotas, rate limits, and cost controls before public production use.
- Do not silently switch users to paid providers or paid endpoints.
- Apply age-appropriate safety and privacy protections when serving minors.
- Do not depend on local model runtimes or user GPUs.

## Development roadmap

### Stage 1 — Real provider integrations

- Verify official API availability and requirements.
- Complete authorization and policy checks.
- Activate at least two eligible real providers.
- Keep Mock available for testing.

### Stage 2 — Multi-model system

- Connect the frontend to the backend orchestration endpoint.
- Support concurrent requests to multiple real providers.
- Display independent model responses and request statuses.

### Stage 3 — Comparison and MVP

- Compare provider responses.
- Complete backend and frontend tests.
- Verify failure handling and security.
- Prepare a limited public beta after a final review.

### Implemented

- Initial frontend dashboard
- Backend health endpoint
- Provider abstraction and registry
- Mock provider
- Provider catalog metadata
- Provider lifecycle management
- OpenAI adapter and factory implementation
- Concurrent multi-provider chat endpoint
- Frontend multi-provider chat interface
- Shared HTTP client infrastructure
- Network security configuration and validation
- HTTP client lifecycle management
- Automated backend and frontend checks

### Pending

- Final OpenAI activation review
- At least one additional eligible real provider
- Successful multi-provider testing with real services
- Production authentication
- User-specific quotas
- Persistent chat history
- Production deployment
- Public beta readiness review

## Project

- **Name:** AI UNIVERSE
- **Type:** Multi-AI platform
- **Status:** Active development
- **Repository:** https://github.com/MehrbodDev/AI-UNIVERSE
