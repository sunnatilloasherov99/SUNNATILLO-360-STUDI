# Development and deployment

## Requirements
- Node.js 20+
- Python 3.12+
- Docker Compose (recommended for PostgreSQL and portable deployment)
- Optional: Ollama installed locally or on a private server for free local AI assistance

## Frontend
```bash
cd frontend
npm install
npm run dev
```

The Vite development server runs on `http://localhost:5173` and proxies `/api` requests to the backend.

## Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health endpoint: `http://localhost:8000/api/health`.

The backend uses SQLite by default for local development. Set `DATABASE_URL`, `MEDIA_STORAGE_PATH` and a strong `JWT_SECRET` through environment variables when needed. Database schema changes are managed by Alembic; do not rely on automatic table creation.

## Optional local AI
Install Ollama on a machine you control, download a model such as `llama3.2`, then set:
- Local backend: `OLLAMA_BASE_URL=http://localhost:11434`
- Backend in Docker with Ollama running on the host: `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- `OLLAMA_MODEL=llama3.2`

No paid API key is required for this local provider. The AI assistant always sends only the prompt and text context the user enters. A project image is sent only if the user explicitly selects it and presses Ask AI; images are limited to 12 MB and require a vision-capable model such as `llava`. Videos are not sent to AI.

## Portable Docker deployment
Copy `infra/.env.example` to `infra/.env`. Set a strong unique PostgreSQL password, a random JWT secret of at least 32 characters, the public frontend origin and any optional Ollama settings. Then run:
```bash
cd infra
docker compose up -d --build
```

The API container runs `alembic upgrade head` before starting FastAPI. Docker Compose also starts a private Redis service for shared request rate limits; local development defaults to in-memory limits. PostgreSQL and media files use separate persistent Docker volumes.

### Backup and restore
Run these from the `infra/` directory on a Linux host with Docker Compose:
```bash
bash backup.sh
bash restore.sh ../backups/studio-db-TIMESTAMP.dump ../backups/studio-media-TIMESTAMP.tar.gz
```
Backups include a PostgreSQL custom-format dump, original media archive and SHA-256 checksums. Store copies off-server in encrypted storage. Restore replaces the current database and media; the script requires typing `RESTORE` before proceeding. Only the web service publishes a host port; the API, PostgreSQL and Redis stay on the private Docker network. Put the web entry point behind HTTPS and keep SSH/firewall access restricted.

## Implemented boundaries
- Account registration/login and per-user project/media access control.
- 360° panorama viewing, non-destructive image adjustments and edited JPEG export.
- Multi-scene virtual-tour builder with clickable scene hotspots.
- Quality report and authenticated ZIP project export.
- MP4/WebM upload and basic equirectangular 360° video playback; no timeline editing or transcoding yet.
- Optional text-only local Ollama AI; no image/video analysis or cloud AI adapters yet.
- Google Street View, Yandex Maps and 2GIS publishing are not yet connected. Publishing must use official APIs and account permissions.
- Production launch still requires rate limiting, email verification/password reset, HTTPS configuration and a tested backup/restore procedure.
