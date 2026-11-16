# Architecture and portability

## Core boundaries
- The React frontend communicates with the FastAPI backend through HTTP APIs.
- Domain logic must not depend on a hosting provider.
- Storage access will use an application storage interface; local filesystem is the initial adapter, with S3-compatible storage as an optional future adapter.
- AI providers will be adapters behind a common internal contract. No provider is mandatory.
- Publishing targets are capability-checked adapters. Never claim a platform can publish tours unless its official API, partner agreement and account permissions allow it.
- Localization dictionaries are the source of truth. Every new UI key must be added to Uzbek, Russian and English.

## Media safety and privacy
- Imported originals are immutable.
- Edits are represented as project instructions and metadata, then rendered to new output files.
- AI suggestions are proposals; applying them requires explicit user approval.
- External AI receives only the minimum selected context after explicit user consent.
- API keys and provider credentials stay server-side, outside frontend bundles and source control.

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
The initial commit establishes a multilingual web shell, startup-mode selection, browser-local project list, FastAPI health endpoint and Docker-based self-hosting baseline. Full media editing, durable server-side projects, authentication, AI adapters, publishing integrations and automated quality analysis are not yet implemented.
