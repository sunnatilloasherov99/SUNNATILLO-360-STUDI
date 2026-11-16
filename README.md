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
- Original imported panorama is not modified.
- Non-destructive brightness, contrast and saturation adjustments can be previewed and saved per project.
- Export adjusted panorama images as new JPEG files while preserving the uploaded original.
- Build private multi-scene virtual tours from uploaded panoramas, reorder scenes and connect them with clickable in-view hotspots.
- Run project quality checks for image integrity, 2:1 panorama ratio, recommended resolution and broken tour links.
- Download an authenticated ZIP archive containing project metadata, tour configuration, edit settings and original media.
- Manual PostgreSQL and media-volume backup/restore scripts with SHA-256 checksums.
- Redis-backed request rate limits for registration, login and AI requests.
- Optional local Ollama AI specialists for panorama advice, tour planning, scene descriptions and stitching guidance; explicitly selected project images can be sent to a vision-capable local model. No paid AI key is required.
- FastAPI health and capability endpoints.
- Server-side project create/list/delete API backed by SQLAlchemy and PostgreSQL (SQLite is available for local development).
- Persistent JPEG/PNG/WebP and MP4/WebM media upload, listing and file delivery endpoints with a configurable upload limit.
- Docker Compose stores uploaded media in a dedicated persistent volume, separate from the database volume.
- Docker Compose baseline with PostgreSQL.
- GitHub Actions frontend build, backend API tests, fresh/legacy database migration checks, backup script syntax and Docker Compose validation.

### Not implemented yet
- Production hardening still required before public launch: email verification/password reset, HTTPS, production secrets and additional abuse monitoring.
- Full timeline editor, video processing, color grading, audio and keyframes.
- Cloud AI provider adapters, multimodal image/video analysis and consent-based project-file context.
- Advanced seam/stitching defect detection and automatic stitching repair.
- Standalone hosted tour publishing and public tour sharing.
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
Docker Compose is the baseline self-hosting path. Configure secrets and public URLs through environment variables; never commit real credentials.
