# SUNNATILLO 360° STUDIO

Independent web platform for professional 360° media editing and virtual-tour production.

## Principles
- Web-first now; desktop packaging can be added later without rewriting the core.
- Self-hostable and portable between hosting providers and domains.
- No mandatory paid AI provider.
- Original media is preserved; edits are non-destructive.
- Uzbek (primary), Russian and English localization.
- External publishing is implemented only where official APIs and permissions support it.

## Repository layout
- `frontend/` — React + TypeScript web application.
- `backend/` — Python + FastAPI application.
- `infra/` — portable deployment configuration.
- `docs/` — architecture and implementation notes.

## Local development
See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Deployment
Docker Compose is the baseline deployment path. Configure secrets and public URLs through environment variables; never commit real credentials.
