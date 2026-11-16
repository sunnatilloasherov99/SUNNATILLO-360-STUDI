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
- First 360° media workspace: import a JPG/PNG/WebP panorama, inspect dimensions and aspect ratio, and interactively look around a 2:1 equirectangular panorama.
- Original imported panorama is not modified.
- FastAPI health and capability endpoints.
- Server-side project create/list/delete API backed by SQLAlchemy and PostgreSQL (SQLite is available for local development).
- Persistent JPEG/PNG/WebP media upload, listing and file delivery endpoints with a configurable upload limit.
- Docker Compose stores uploaded media in a dedicated persistent volume, separate from the database volume.
- Docker Compose baseline with PostgreSQL.
- GitHub Actions frontend build and backend syntax checks.

### Not implemented yet
- User accounts, project ownership and access control (not yet implemented).
- Full timeline editor, video processing, color grading, audio and keyframes.
- AI provider adapters and consent-based shared project context.
- Stitching repair and automated quality analysis.
- Google Street View publishing OAuth/upload workflow.
- Yandex Maps and 2GIS publishing adapters.
- Export bundles, backups and desktop packaging.

The current panorama viewer is a first editing milestone, not a complete professional editor or a direct publishing tool.

## Repository layout
- `frontend/` — React + TypeScript web application.
- `backend/` — Python + FastAPI application.
- `infra/` — portable Docker deployment configuration.
- `docs/` — architecture and development notes.

## Local development
See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Deployment
Docker Compose is the baseline self-hosting path. Configure secrets and public URLs through environment variables; never commit real credentials.
