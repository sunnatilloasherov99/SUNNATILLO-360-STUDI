# SUNNATILLO 360° STUDIO

An independent, portable web platform for professional 360° media workflows and virtual-tour production.

## Product principles
- Web-first now; desktop application later, reusing the same domain and project formats.
- Self-hostable and portable between hosting providers and domains.
- No mandatory paid AI provider.
- Original media is preserved; edits are non-destructive.
- Uzbek (primary), Russian and English localization.
- External publishing is implemented only where official APIs and account permissions support it.

## Current implementation status

### Working foundation
- React + TypeScript web interface.
- Uzbek, Russian and English language selector with persistent preference.
- Three project startup modes: AI Professional, Manual Professional and AI Collaboration.
- Server-backed project creation and listing through the FastAPI API.
- 360° photo workspace: import JPG/PNG/WebP panoramas, inspect dimensions and aspect ratio, and interactively look around 2:1 equirectangular images.
- Initial 360° video workspace: upload MP4/WebM, preview equirectangular footage on an interactive Three.js sphere, drag to look around and use playback controls.
- Save non-destructive 360° video trim in/out markers per project, preview the selected range and export the trimmed result as MP4 with server-side FFmpeg; the original video remains unchanged.
- Original imported panorama is not modified.
- Non-destructive brightness, contrast and saturation adjustments can be previewed and saved per project.
- Horizontal seam repositioning can be previewed and exported to a new JPEG without overwriting the source; it moves the panorama edge but does not reconstruct missing pixels.
- Export adjusted panorama images as new JPEG files while preserving the uploaded original.
- Build multi-scene virtual tours from uploaded panoramas, reorder scenes and connect them with clickable in-view hotspots.
- Create revocable public tour links; public viewers can navigate scenes and hotspots without logging in.
- Run project quality checks for image integrity, 2:1 panorama ratio, recommended resolution and broken tour links.
- Download an authenticated ZIP archive containing project metadata, tour configuration, edit settings and original media.
- Manual PostgreSQL and media-volume backup/restore scripts with SHA-256 checksums.
- Redis-backed request rate limits for registration, login and AI requests.
- Installable Progressive Web App (PWA) shell for desktop/mobile browsers; private API data is never cached by the service worker.
- Optional local Ollama AI specialists for panorama advice, tour planning, scene descriptions and stitching guidance, plus a three-role parallel collaboration review; explicitly selected project images can be sent to a vision-capable local model. No paid AI key is required.
- FastAPI health and capability endpoints.
- Server-side project create/list/delete API backed by SQLAlchemy and PostgreSQL (SQLite is available for local development).
- Persistent JPEG/PNG/WebP and MP4/WebM media upload, listing and file delivery endpoints with a configurable upload limit.
- Docker Compose stores uploaded media in a dedicated persistent volume, separate from the database volume.
- Docker Compose baseline with PostgreSQL.
- GitHub Actions frontend build, backend API tests, fresh/legacy database migration checks, backup script syntax and Docker Compose validation.

### Not implemented yet
- Production hardening still required before public launch: email verification/password reset, HTTPS, production secrets and additional abuse monitoring.
- Full multi-track timeline editor, advanced color grading, audio editing and keyframes; current MP4 export is a basic trim-and-re-encode workflow.
- Cloud AI provider adapters, multimodal image/video analysis and consent-based project-file context.
- Advanced seam/stitching defect detection and automatic stitching repair.
- Standalone offline tour package export and official Google/Yandex/2GIS publishing integrations.
- Google Street View publishing OAuth/upload workflow.
- Yandex Maps and 2GIS publishing adapters.
- Scheduled automatic backups, automated restore drills and desktop packaging.

The current panorama viewer is a first editing milestone, not a complete professional editor or a direct publishing tool.

## Repository layout
- `frontend/` — React + TypeScript web application.
- `backend/` — Python + FastAPI application.
- `infra/` — portable Docker deployment configuration.
- `docs/` — architecture and development notes.

## Local development
See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Deployment
Docker Compose is the baseline self-hosting path. Configure secrets and public URLs through environment variables; never commit real credentials. The optional `production` profile adds Caddy automatic HTTPS: point your domain to the VPS, set `DOMAIN` and `FRONTEND_ORIGIN` in `infra/.env`, open TCP 80/443, then run `docker compose --profile production --env-file .env -f docker-compose.yml up -d --build` from `infra/`. The API, database and Redis remain private; only Caddy is publicly exposed.
