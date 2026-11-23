
# AI UNIVERSE

**Multi-AI Command Center**

AI UNIVERSE is a multi-provider AI workspace in active development. Its goal is to bring supported cloud AI services and AI workflows into one unified interface.

> **Current status:** The project includes an initial dashboard, provider architecture, shared HTTP client infrastructure, and a security-focused provider transport layer. The backend currently uses a mock provider only. No real AI provider integration is enabled.

## Project goals

- A unified workspace for supported AI services
- Compare model responses through an AI Arena
- Research, learning, coding, and knowledge workflows
- Provider-independent backend architecture
- Account-level usage limits, cost controls, and privacy safeguards
- Secure and maintainable communication with external provider APIs

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

The backend is built with FastAPI and currently includes:

- Health endpoint: `GET /api/health`
- Provider listing: `GET /api/providers`
- Provider catalog: `GET /api/providers/catalog`
- Chat endpoint: `POST /api/chat`
- Provider abstraction through `BaseProvider`
- Provider registration and lookup through `ProviderRegistry`
- `MockProvider` for local architecture testing
- Pydantic-based provider schemas
- Shared asynchronous HTTP client infrastructure
- Provider HTTP transport layer
- Centralized network security configuration and validation
- Secure transport lifecycle management
- Automated tests for HTTP client behavior, network security, and provider transport

The chat endpoint currently uses the mock provider. It does not call OpenAI, Gemini, or any other external AI service.

### HTTP and network security

The backend includes shared infrastructure for outbound HTTP communication.

The current implementation focuses on:

- Centralized HTTP client configuration
- Secure transport configuration and TLS-related validation
- Timeout configuration validation
- Consistent provider transport behavior
- HTTP client lifecycle management
- Automated security and transport integration tests

The transport infrastructure is intended to provide a consistent foundation for future provider integrations. It does not mean that external providers are currently connected.

Some transport compatibility checks rely on HTTPX and HTTPCore implementation details. Dependency upgrades should therefore be accompanied by compatibility and security test runs.

### Frontend

- Next.js App Router
- React and TypeScript
- Tailwind CSS
- Dashboard interface
- Backend health check against `http://127.0.0.1:8010/api/health`

The AI workspace modules are interface placeholders unless explicitly stated otherwise. A visible module card does not mean its underlying feature is implemented.

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
- Integrate providers only through authorized official APIs or permitted official workspaces.
- Respect provider terms, age requirements, regional restrictions, and licensing.
- Apply authentication, per-user quotas, rate limits, and cost controls before public production use.
- Do not silently switch users to paid providers or paid endpoints.
- Do not depend on local model runtimes or user GPUs.

## Development status

### Implemented

- Initial frontend dashboard
- Backend health endpoint
- Provider abstraction and registry
- Mock provider
- Provider catalog metadata
- Shared HTTP client infrastructure
- Provider HTTP transport layer
- Network security configuration and validation
- HTTP client lifecycle management
- Automated backend tests for provider, HTTP client, and network security components

### Not yet implemented

- Real provider API integrations
- Production authentication
- User-specific quotas
- Persistent chat history
- Model routing
- Multi-model orchestration
- Production deployment

## Project

- **Name:** AI UNIVERSE
- **Type:** Multi-AI platform
- **Status:** Active development
- **Repository:** https://github.com/MehrbodDev/AI-UNIVERSE
