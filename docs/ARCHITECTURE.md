# Architecture and portability

## Core boundaries
- The React frontend communicates with the FastAPI backend through HTTP APIs.
- Domain logic must not depend on a hosting provider.
- Storage access uses the local filesystem adapter initially; S3-compatible storage can be added without changing domain logic.
- AI providers will be adapters behind a common internal contract. No provider is mandatory.
- Publishing targets are capability-checked adapters. Never claim a platform can publish tours unless its official API, partner agreement and account permissions allow it.
- Localization dictionaries are the source of truth. Every new UI key must be added to Uzbek, Russian and English.

## Media safety and privacy
- Imported originals are immutable.
- Initial panorama adjustments (brightness, contrast and saturation) are stored as project settings and previewed non-destructively; they do not overwrite source files.
- Edits are represented as project instructions and metadata, then rendered to new output files.
- AI suggestions are proposals; applying them requires explicit user approval.
- External AI receives only the minimum selected context after explicit user consent.
- API keys and provider credentials stay server-side, outside frontend bundles and source control.
- Account registration, login and current-user endpoints use signed, expiring JWT bearer tokens.
- Project and media endpoints require authentication and enforce project ownership; media files are not publicly readable.
- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, never in plaintext.
- Set a unique, random `JWT_SECRET` (at least 32 characters) before deployment; the development fallback is not suitable for production.

## Persistence
- Projects and media metadata are stored through SQLAlchemy; PostgreSQL is the Docker default and SQLite is available for local development.
- Original media files are stored in a configurable persistent directory.
- Docker Compose uses separate persistent volumes for the database and media files.
- Database schema changes currently use SQLAlchemy `create_all`; Alembic migrations are required before production use.

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
Implemented foundation: multilingual web shell, startup-mode selection, server-backed project CRUD, persistent panorama upload/listing, 360° panorama viewer and Docker self-hosting baseline. Not yet implemented: user authentication and project ownership, full media editing, AI adapters, publishing integrations, automated quality analysis, export bundles and backup tooling.
