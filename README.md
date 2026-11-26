# AI UNIVERSE

**Multi-AI Command Center**

AI UNIVERSE is a multi-provider AI workspace designed to bring supported AI services into one unified interface. The project focuses on provider-independent architecture, concurrent model requests, independent response handling, and secure API communication.

> **Development status:** AI UNIVERSE is under active development. The backend includes a working provider registry and lifecycle system, concurrent multi-provider orchestration, a Mock provider, and an implemented OpenAI adapter. The Mock provider is currently the only registered runtime provider. External provider activation and integration verification are postponed.

## Project goals

- Provide a unified workspace for supported AI services.
- Compare responses from different AI models.
- Support concurrent requests to multiple providers.
- Build a provider-independent backend architecture.
- Provide secure and maintainable communication with external APIs.
- Introduce usage limits, cost controls, and privacy safeguards before public deployment.

## Provider catalog

AI UNIVERSE currently tracks the following 11 planned external providers:

1. OpenAI
2. Google Gemini
3. xAI Grok
4. Microsoft Copilot
5. DeepSeek
6. Alibaba Qwen
7. Anthropic Claude
8. Z.ai GLM
9. Moonshot AI Kimi
10. Mistral AI
11. Perplexity

The provider catalog represents planned integrations, not active connections.

Every provider must pass technical, API availability, regional, licensing, age-policy, and authorization checks before activation.

### Current provider status

| Provider           | Implementation                  | Runtime status                       |
| ------------------ | ------------------------------- | ------------------------------------ |
| Mock               | Implemented                     | Registered and available for testing |
| OpenAI API         | Adapter and factory implemented | Not registered                       |
| Other 10 providers | Planned                         | Not implemented                      |

The project currently uses Mock for multi-provider orchestration testing. External provider activation and integration verification are postponed.

A provider listed in the catalog is not necessarily connected or operational.

## Current implementation

### Backend

The backend is built with FastAPI and includes:

- `GET /` — Backend root and version information
- `GET /api/health` — Backend health check
- `GET /api/providers` — Registered providers
- `GET /api/providers/catalog` — Provider catalog
- `GET /api/providers/lifecycle` — Provider lifecycle information
- `POST /api/chat` — Single-provider chat
- `POST /api/chat/multi` — Concurrent multi-provider chat

The backend architecture includes:

- Provider abstraction through `BaseProvider`
- Provider registration and lookup through `ProviderRegistry`
- Provider creation through `ProviderFactory`
- Provider lifecycle validation
- Pydantic-based request and response schemas
- Independent result and error handling
- Shared asynchronous HTTP client infrastructure
- Centralized network security configuration
- Structured provider error handling

### Provider registry and lifecycle

The provider registry and lifecycle system supports:

- Provider registration and lookup
- Provider configuration validation
- Provider availability checks
- Runtime lifecycle status reporting
- Separation between catalog entries and registered providers
- Mock provider registration without external API credentials

The Mock provider is currently the only registered runtime provider.

### Multi-provider orchestration

The multi-chat endpoint accepts requests targeting between 2 and 5 providers.

Example request:

```json
{
  "message": "What is artificial intelligence?",
  "providers": ["mock", "openai"]
}
```

This example demonstrates the request format. Both providers must be registered and available for successful execution.

The backend:

- Runs provider requests concurrently.
- Keeps each provider result independent.
- Reports successful and failed requests separately.
- Returns provider and model information.
- Provides structured error information.
- Handles unregistered providers.
- Handles invalid provider responses.
- Isolates unexpected provider exceptions.
- Prevents one provider failure from hiding other results.
- Preserves compatibility with the existing single-provider chat endpoint.

The endpoint supports a maximum of five providers per request.

### OpenAI integration

The project contains an OpenAI adapter based on the official Responses API.

Implemented capabilities include:

- Configurable API key
- Configurable model
- Configurable timeout
- Optional base URL
- Shared HTTP client injection
- Response parsing and validation
- Provider-specific error handling
- Secure handling of API credentials
- `store: false` in Responses API requests

The adapter and factory are implemented, but OpenAI is not currently registered in the active provider registry.

External API activation and integration verification are postponed.

### HTTP and network security

The backend includes shared infrastructure for outbound HTTP communication.

Current implementation focuses on:

- Centralized HTTP client configuration
- TLS certificate verification
- Hostname validation
- DNS validation and secure transport controls
- Timeout configuration validation
- Consistent provider transport behavior
- HTTP client lifecycle management
- Restricted redirect behavior
- Controlled retry handling
- Automated security and transport integration tests

Dependency upgrades should be accompanied by compatibility and security test runs.

## Frontend

The frontend is built using:

- Next.js App Router
- React
- TypeScript
- Tailwind CSS

The current frontend includes an initial multi-provider testing interface.

Current functionality includes:

- Provider availability information
- Provider selection
- Selection of 2 to 5 providers
- Backend API communication
- Multi-provider test workflow

The frontend currently reflects the backend runtime state: Mock is available, while external providers remain planned or inactive.

Further frontend work includes:

- Improved comparison interface
- Independent provider response presentation
- Success and failure status display
- Structured error information
- Loading and request-state handling
- Chat history controls

Frontend functionality must be fully verified before the project is considered ready for public beta.

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

The frontend API base URL should point to the local backend:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8010/api
```

Place this configuration in `frontend/.env.local`.

## Environment configuration

Provider settings are loaded from `backend/.env`.

OpenAI configuration uses the following environment variable names:

```dotenv
AI_UNIVERSE_OPENAI_ENABLED=false
AI_UNIVERSE_OPENAI_API_KEY=
AI_UNIVERSE_OPENAI_MODEL=
AI_UNIVERSE_OPENAI_TIMEOUT=30
```

These are example values, not active credentials.

Important:

- Never commit `.env` files.
- Never put API keys in frontend code.
- Never paste API keys into source files or public issue trackers.
- Only use credentials with valid authorization from the account owner.
- Do not activate a provider until its required checks have passed.

## Tests and quality checks

### Backend tests

Run the complete backend test suite:

```powershell
cd "$HOME\AI-UNIVERSE\backend"

.\.venv\Scripts\python.exe -m pytest
```

**Latest verified backend test result (November 26, 2026):**

- Total tests: 446
- Passed: 446
- Failed: 0
- Skipped: 0

The test suite includes coverage for:

- API endpoints
- Provider registry and lifecycle
- Provider adapters and contracts
- Multi-provider orchestration
- HTTP client behavior
- Network security
- Secure transport
- Error handling and retry behavior

The latest test run reported one non-blocking Starlette deprecation warning related to HTTPX compatibility.

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

## Security and usage principles

- Keep provider API keys on the backend only.
- Never commit `.env` files, credentials, or tokens.
- Do not expose secrets in frontend code or browser responses.
- Verify TLS certificates for external HTTPS connections.
- Use explicit and validated timeout settings for outbound requests.
- Manage shared HTTP clients through their intended application lifecycle.
- Integrate providers only through authorized official APIs.
- Respect provider terms, licensing, age requirements, and regional restrictions.
- Do not silently switch users to paid providers or paid endpoints.
- Apply authentication, per-user quotas, rate limits, and cost controls before public production use.
- Do not depend on local model runtimes or user GPUs.

### Age eligibility

AI UNIVERSE is intended exclusively for adults aged 18 and older.

Access restrictions must be implemented and enforced before public availability. Users below the age of 18 are not eligible to use the product.

Provider-specific age requirements and regional restrictions must also be respected.

## Development roadmap

### Stage 1 — Provider Registry and Lifecycle

- Implement provider registration and lookup.
- Validate provider configuration.
- Implement provider lifecycle checks.
- Separate catalog entries from active runtime providers.
- Support Mock provider registration and testing.

**Status: Completed.**

### Stage 2 — Multi-Provider Orchestration

- Implement concurrent multi-provider requests.
- Support 2 to 5 providers per request.
- Isolate individual provider failures.
- Validate provider responses.
- Handle unexpected provider exceptions.
- Preserve the legacy single-provider chat endpoint.
- Add automated orchestration tests.

**Status: Completed.**

### Stage 3 — Frontend Comparison UI and MVP Validation

- Complete the multi-provider comparison interface.
- Improve independent response presentation.
- Improve loading and error states.
- Verify frontend and backend integration.
- Complete frontend quality checks.
- Perform end-to-end MVP validation.
- Review production safeguards before considering a public beta.

**Status: In progress.**

### Future development

- Verify official API availability and requirements.
- Complete authorization and policy checks.
- Activate eligible external providers when integration work resumes.
- Test multi-provider requests with real services.
- Implement production authentication.
- Introduce user-specific quotas and cost controls.
- Implement persistent chat history.
- Prepare production deployment.
- Conduct a public beta readiness review.

External provider activation is intentionally postponed and is not a requirement for completing the current three development stages.

## Project information

- **Name:** AI UNIVERSE
- **Type:** Multi-AI platform
- **Status:** Active development
- **Target audience:** Adults aged 18 and older
- **Repository:** https://github.com/MehrbodDev/AI-UNIVERSE
