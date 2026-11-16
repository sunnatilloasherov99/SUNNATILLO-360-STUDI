# Architecture and portability

## Core boundaries
- The React frontend communicates with the FastAPI backend through HTTP APIs.
- Domain logic must not depend on a hosting provider.
- Storage access uses the local filesystem adapter initially; S3-compatible storage can be added without changing domain logic.
- AI providers will be adapters behind a common internal contract. No provider is mandatory.
- The optional Ollama adapter runs on the user's own server and requires no paid API key. It sends explicitly entered text and can include a project image only when the user selects it for a request (12 MB limit, vision-capable model required). A collaboration mode queries quality, stitching and tour-planning roles in parallel. Videos are not sent.
- Publishing targets are capability-checked adapters. Never claim a platform can publish tours unless its official API, partner agreement and account permissions allow it.
- Localization dictionaries are the source of truth. Every new UI key must be added to Uzbek, Russian and English.

## Media safety and privacy
- Imported originals are immutable.
- Initial MP4/WebM equirectangular video playback uses a local Three.js sphere viewer. Project-saved trim in/out markers can be previewed and exported as a new MP4 through server-side FFmpeg; the source video remains unchanged. This is a basic single-range trim workflow, not a full multi-track timeline editor, advanced colour-grading suite or keyframe editor.
- Initial panorama adjustments (brightness, contrast, saturation and horizontal seam repositioning) are stored as project settings and previewed non-destructively; they do not overwrite source files. Seam repositioning moves the left/right boundary and is not AI inpainting or seam reconstruction.
- Edited images are exported as new JPEG files; uploaded originals remain untouched.
- Multi-scene tour configuration, scene order and scene-to-scene hotspot links are stored per project and validated against media owned by that project.
- Owners can enable or revoke a random-token public tour link; public tour metadata and image delivery are restricted to the shared project and rate-limited.
- Authenticated quality reports inspect original image integrity, panorama aspect ratio, recommended width and tour references.
- Authenticated project ZIP exports package metadata, edit settings, tour configuration and available original media.
- Edits are represented as project instructions and metadata, then rendered to new output files.
- AI suggestions are proposals; applying them requires explicit user approval.
- External AI receives only the minimum selected context after explicit user consent.
- API keys and provider credentials stay server-side, outside frontend bundles and source control.
- Account registration, login and current-user endpoints use signed, expiring JWT bearer tokens.
- Project and media endpoints require authentication and enforce project ownership; media files are not publicly readable.
- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, never in plaintext.
- Set a unique, random `JWT_SECRET` (at least 32 characters) before deployment; production startup rejects the development fallback or a shorter secret.
- Registration, login and AI endpoints have Redis-backed rate limits in Docker deployments (in-memory storage for local development).
- Before public launch, add email verification and password reset, HTTPS, production monitoring and a tested backup/restore procedure.

## Persistence
- Projects and media metadata are stored through SQLAlchemy; PostgreSQL is the Docker default and SQLite is available for local development.
- Original media files are stored in a configurable persistent directory.
- Docker Compose uses separate persistent volumes for the database and media files.
- Database schema changes are managed through Alembic migrations; the API container applies pending migrations before startup.

## Portability
- Docker Compose defines the baseline self-hosted deployment.
- Configuration and secrets are environment-driven.
- Database and media backups are separate, documented and restorable.
- No production domain, absolute host path or provider-specific SDK is hardcoded into application logic.
- Desktop packaging can later wrap the web client while reusing the same domain/API contracts.

## Planned modules
1–18. Studio editor foundation and media workflow.
19. Uzbek, Russian and English localization.
20. 360° Tour Publisher.
21. AI Professional, Manual Professional and AI Collaboration startup modes.
22. Shared project context and privacy controls.
23. Final project quality control.
24. Editable project delivery, exports and backup.

## Current status
Implemented foundation: multilingual web shell, email account registration/login, JWT-protected project and media ownership, persistent panorama upload/listing, 360° panorama viewer, non-destructive image adjustments, edited-image export, multi-scene virtual tour builder with clickable hotspots, authenticated quality reports and ZIP project export. Remaining: full timeline/video editing, cloud and multimodal AI adapters, official publishing integrations, advanced seam repair, automated backups and desktop packaging.
