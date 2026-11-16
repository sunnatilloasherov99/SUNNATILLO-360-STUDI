# Panorama repair implementation plan

## Goal

Add a safe, practical repair workflow for already-stitched 360-degree panoramas, especially phone-captured images with visible joins, exposure differences, ghosting, or small stitching defects.

This module must improve an existing equirectangular image without silently changing or replacing the uploaded original. It must not promise recovery of scene details that are absent from the source pixels.

## Current baseline (verified in the code)

- The editor supports brightness, contrast, saturation, horizontal seam repositioning, and a small edge-feather blend.
- The current seam score compares only the first and last image columns.
- The automatic seam locator searches for a low-contrast vertical position; it does not detect or repair internal stitching defects.
- The optional Ollama vision integration can analyze a selected image and return advice. It does not generate repaired pixels.
- Export and save-copy operations create a new JPEG while retaining the uploaded source.

## Design principles

1. **Original is immutable.** Every repair is a new derived asset with a link to its source asset and a record of applied operations.
2. **Preview before apply.** All repair operations are previewed; the user explicitly confirms saving a copy.
3. **360-aware coordinates.** Horizontal coordinates wrap at 0°/360° so a repair crossing the panorama boundary is treated as one continuous region.
4. **Honest diagnostics.** Distinguish measurable edge discontinuities from suspected parallax, ghosting, blur, or missing content. A heuristic must never be described as a definitive AI diagnosis.
5. **Local-first and optional AI.** Core manual tools must work without a paid API. Optional local AI/inpainting providers are adapters and must be explicitly enabled.
6. **Bounded processing.** Enforce image dimension, pixel-count, memory, and processing-time limits; reject malformed or unsupported files safely.

## Delivery milestones

### 5.1 — Diagnostic foundation
- Add deterministic image-analysis helpers with unit tests and synthetic fixtures.
- Report equirectangular suitability, resolution, outer-edge mismatch, and candidate internal vertical discontinuities.
- Include confidence/limitations in every diagnostic result.
- Do not auto-edit an image from a diagnostic result.

### 5.2 — Manual repair tools
- Add a brush/patch workflow for small defects, with undo/redo and adjustable brush size/feather.
- Support wrap-aware editing across the left/right panorama boundary.
- Offer clone/heal from a user-selected source region before any generative fill.
- Store edits as a reproducible operation history.

### 5.3 — Optional AI inpainting adapter
- Define a provider-neutral interface for masked image repair.
- First support a locally hosted inpainting service (for example, a user-configured local ComfyUI endpoint); no paid provider is required by default.
- Require the user to paint/confirm the repair mask and preview generated results.
- Keep credentials server-side, enforce timeouts/size limits, and never send images to an external provider without explicit consent.
- If no compatible local model is configured, clearly disable this option and keep manual tools available.

### 5.4 — Export and regression validation
- Save repaired output as a new asset with source linkage and edit metadata.
- Add tests for boundary wrapping, mask bounds, original-file immutability, ownership checks, malformed images, and output dimensions.
- Validate with real user-supplied panoramas before claiming quality improvements.

## Acceptance criteria

- A repair never overwrites the original upload.
- A user can inspect before/after and cancel without changing project media.
- A repair mask crossing the 0°/360° boundary behaves continuously.
- The system clearly labels heuristic candidates and AI-generated content.
- Automated tests cover the image-processing helpers and API security.
- No paid API key is required for diagnostics or manual repair.

## Known limits

A stitched panorama cannot reliably reconstruct an object that was never captured, was fully occluded, or was lost during stitching. Generative inpainting may invent plausible pixels; it must be presented as generated content and reviewed by the user. Severe parallax and duplicated people/objects may require the original source photos and a dedicated stitching workflow rather than editing the flattened panorama.
