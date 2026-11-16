# Panorama editor — browser acceptance checklist

This checklist is for the real-browser acceptance pass in stage 5. It complements CI: a passing build does not prove that pointer drawing, canvas compositing, downloads, or visual quality work correctly in a real browser.

## Test setup

- Use a desktop browser with the application running against a test account and test project.
- Keep an untouched copy of the original 2:1 equirectangular panorama.
- Prefer a panorama with a visible but repairable defect near the center and another near the left/right 360° boundary.
- Record browser/version, source dimensions, source file size, and whether local inpainting is configured.
- Do not use a production-only or irreplaceable original for acceptance testing.

## A. Import and original-file protection

1. Upload a JPG, PNG, or WebP panorama to a project.
2. Confirm the viewer opens and reports the image dimensions and aspect ratio.
3. Save or download the original asset before editing; calculate or record its file hash if practical.
4. Re-open the project and confirm the original asset is still available.

**Pass:** the source can be viewed and the original asset remains independently available.

## B. Manual clone-brush repair

1. Open the panorama repair editor.
2. Select a clean source area, then paint over a small defect.
3. Test at least two brush sizes.
4. Use undo, redo, and clear; verify each operation changes only the repair overlay.
5. Repeat once with the target defect near the left edge and the source area near the right edge, then reverse them.
6. Change the interface language while repairs exist; verify the repair strokes remain.
7. Switch to another source image and back; verify stale strokes do not appear on the wrong image.

**Pass:** source sampling and target painting wrap horizontally at the 360° boundary; undo/redo/clear behave predictably; the original pixels remain unchanged.

## C. Optional AI inpainting

Run this section only when an authorized local provider/HTTP bridge is configured.

1. With the provider disabled, confirm the AI action is unavailable and manual repair still works.
2. With the provider enabled, paint a small white mask over a defect.
3. Confirm the consent prompt appears before upload.
4. Cancel once and verify no AI request is made.
5. Confirm and run the repair; verify the provider receives the original image plus a binary mask (black outside, white inside).
6. Review the returned image in the before/after preview.
7. Reject one result and confirm the editor returns to the original source.
8. Generate another result and accept it; confirm the accepted result becomes the working base.
9. Change the source image while a request is in progress; confirm a stale response cannot replace the new image.

**Pass:** AI is opt-in, only the selected image and mask are sent to the configured provider, the result is previewed before acceptance, and rejection leaves the source unchanged.

## D. Export composition

1. Start from a fresh copy of the test panorama.
2. Apply a visible brightness/contrast/saturation adjustment.
3. Accept an AI result if the provider is available.
4. Add a clone-brush repair.
5. Set a non-zero seam offset and a small seam feather value.
6. Export the edited JPEG.
7. Open the exported JPEG in a separate image viewer and inspect the edited areas, image dimensions, left/right boundary, and overall colour.
8. Save the edited copy to the project library.
9. Confirm the saved derivative identifies its source asset.
10. Re-open/download the original and compare its hash or pixels with the pre-edit copy.

**Pass:** the exported/saved derivative contains the accepted edits in the intended order; the original remains byte-for-byte unchanged; the derivative is linked to the correct source asset.

## E. Browser/device coverage

- Desktop Chrome or Edge: full pass.
- Desktop Firefox: import, brush, undo/redo, preview, export smoke test.
- Mobile browser: import, touch drawing, scroll/zoom interaction, and export smoke test.
- Repeat the 360° seam tests with a real phone panorama before closing stage 5.

## Results record

For each section record: Pass / Fail / Not run, browser and device, source panorama dimensions, screenshots of visual defects, and any console/network errors. Do not mark stage 5 complete while sections B and D fail, or while real-panorama visual acceptance remains untested.

## Known dependency

The optional AI section cannot pass until a local inpainting provider or compatible HTTP bridge is configured. The application currently exposes a generic authenticated multipart HTTP adapter; it is not a direct ComfyUI workflow integration.
