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

No paid API key is required for this local provider. The AI assistant sends only the prompt, text context and media the user explicitly selects before pressing Ask AI. Images are limited to 12 MB; videos are limited to 100 MB and 30 minutes. For video analysis, FFmpeg extracts three chronological keyframes (10%, 50%, 90%); only those frames are sent to the local Ollama vision model. No full video is uploaded to an external AI provider.

## Portable Docker deployment
Copy `infra/.env.example` to `infra/.env`. Set a strong unique PostgreSQL password, a random JWT secret of at least 32 characters, the public frontend origin and any optional Ollama settings. Then run:
```bash
cd infra
docker compose up -d --build
```

The API container runs `alembic upgrade head` before starting FastAPI. After deployment over HTTPS, desktop users can install the PWA from the browser's address-bar install icon or browser menu; mobile users can use Add to Home Screen. Docker Compose also starts a private Redis service for shared request rate limits; local development defaults to in-memory limits. PostgreSQL and media files use separate persistent Docker volumes.

### Production HTTPS deployment

The normal Compose setup publishes the web service only on loopback at `127.0.0.1:WEB_PORT`. For a public VPS, set `DOMAIN` to a domain whose DNS A/AAAA records point to the server, set `FRONTEND_ORIGIN=https://DOMAIN`, open inbound TCP 80/443, copy `infra/.env.example` to `infra/.env`, replace all secrets, then run:

```bash
docker compose --profile production --env-file .env -f docker-compose.yml up -d --build
```

Run the command from `infra/`. The optional Caddy profile obtains and renews HTTPS certificates automatically. Keep the API, PostgreSQL and Redis private; only Caddy publishes ports 80/443. Caddy certificates and keys are stored in persistent Docker volumes.

### Backup and restore
Run these from the `infra/` directory on a Linux host with Docker Compose:
```bash
bash backup.sh
bash restore.sh ../backups/studio-db-TIMESTAMP.dump ../backups/studio-media-TIMESTAMP.tar.gz
```
Backups include a PostgreSQL custom-format dump, original media archive and SHA-256 checksums. Store copies off-server in encrypted storage. Restore replaces the current database and media; the script requires typing `RESTORE` before proceeding. Only the web service publishes a host port; the API, PostgreSQL and Redis stay on the private Docker network. Put the web entry point behind HTTPS and keep SSH/firewall access restricted.

## Implemented boundaries
- Installable PWA shell for desktop/mobile browsers; offline mode caches only the app shell, not private API data.
- Account registration/login and per-user project/media access control.
- 360° panorama viewing, non-destructive brightness/contrast/saturation, seam repositioning and edited JPEG export.
- Multi-scene virtual-tour builder with clickable scene hotspots and revocable public viewing links.
- Quality report and authenticated ZIP project export.
- MP4/WebM upload and equirectangular 360° preview with project-saved non-destructive trim markers. The Video Studio exports the selected range as a new MP4 using FFmpeg; the original stays unchanged. Export is limited to 30-minute source videos and has a 15-minute processing timeout. Full multi-track editing, advanced color grading and keyframes are not implemented yet.
- Optional local Ollama AI specialists and parallel three-role collaboration; selected project images and three extracted video keyframes can be analyzed with a vision-capable model. Cloud AI provider adapters are not yet implemented.
- Google Street View, Yandex Maps and 2GIS publishing are not yet connected. Publishing must use official APIs and account permissions.
- Remaining production tasks: email verification/password reset, automated backup scheduling and restore drills, final domain/DNS setup and live deployment. Manual backup/restore scripts and Redis-backed rate limits are implemented.
