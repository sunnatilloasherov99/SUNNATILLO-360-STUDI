# Development

## Requirements
- Node.js 20+
- Python 3.11+
- Docker Compose (for PostgreSQL / container deployment)

## Frontend
```bash
cd frontend
npm install
npm run dev
```

## Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health endpoint: `http://localhost:8000/api/health`.

## Portable deployment
Copy `infra/.env.example` to `infra/.env`, set a strong unique database password and the real frontend origin, then run:

```bash
cd infra
docker compose up -d --build
```

Production web hosting should serve the built frontend over HTTPS and route `/api` to the API service. Keep the domain in environment/configuration, not in source code. Back up the PostgreSQL volume and media storage separately before moving servers.

## Current implementation boundary
This commit establishes the application shell, three-language dictionary structure, local project-list prototype, API health endpoint and portable container baseline. The full media editor, persistent project API, authentication, AI providers and platform publishing integrations are subsequent implementation milestones—not yet implemented.
