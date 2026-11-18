# AI UNIVERSE — Frontend

The AI UNIVERSE frontend is a Next.js application that provides the platform dashboard and the starting point for its AI workspace modules.

## Requirements

- Node.js LTS
- npm

## Install dependencies

```powershell
npm ci
```

## Development server

```powershell
npm run dev
```

Open `http://localhost:3000`.

## Backend connection

The dashboard checks the FastAPI health endpoint at:

`http://127.0.0.1:8010/api/health`

Start the backend separately from the `backend` directory. If the backend is not running, the dashboard reports the connection as offline.

## Available scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the local development server |
| `npm run lint` | Run ESLint |
| `npm run build` | Create a production build |
| `npm run start` | Start the production server |

## Current scope

The dashboard is implemented, but most workspace modules are interface placeholders. The backend currently exposes a mock provider; no real cloud AI provider is connected.

Provider integrations must be reviewed for official API access, terms, age and regional requirements before being enabled.

## Technology

- Next.js App Router
- React
- TypeScript
- Tailwind CSS