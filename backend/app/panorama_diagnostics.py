"""Heuristic diagnostics for vertical discontinuities in equirectangular panoramas.

These measurements identify candidate boundaries only. They cannot distinguish a
stitching defect from a real vertical edge in the photographed scene.
"""
from __future__ import annotations

from PIL import Image


def find_vertical_discontinuities(
    image: Image.Image,
    *,
    max_width: int = 512,
    max_candidates: int = 5,
    min_separation: int = 12,
) -> dict:
    """Return high-contrast vertical boundary candidates in a 2:1 panorama."""
    width, height = image.size
    if width < 4 or height < 2 or abs(width / height - 2) >= 0.02:
        return {
            "available": False,
            "reason": "not_equirectangular",
            "candidates": [],
            "confidence": "low",
        }

    sample_width = min(max_width, width)
    sample_height = max(2, round(height * sample_width / width))
    preview = image.convert("RGB").resize(
        (sample_width, sample_height), Image.Resampling.LANCZOS
    )
    pixels = preview.load()
    y_start = max(0, int(sample_height * 0.08))
    y_end = min(sample_height, max(y_start + 1, int(sample_height * 0.92)))

    # Include x=0 as the wrap boundary between the final and first columns.
    scores: list[tuple[float, int]] = []
    for x in range(sample_width):
        left_x = (x - 1) % sample_width
        total = 0.0
        count = 0
        for y in range(y_start, y_end):
            left = pixels[left_x, y]
            right = pixels[x, y]
            total += sum(abs(left[c] - right[c]) for c in range(3)) / 3
            count += 1
        scores.append((total / max(1, count), x))

    # Greedy non-maximum suppression prevents adjacent columns from being
    # reported as separate candidates for one strong vertical edge.
    candidates: list[dict] = []
    for score, x in sorted(scores, reverse=True):
        if any(
            min(abs(x - item["x_px"]), sample_width - abs(x - item["x_px"]))
            < min_separation
            for item in candidates
        ):
            continue
        candidates.append({
            "x_px": x,
            "position": round(x / sample_width, 4),
            "longitude_degrees": round(x / sample_width * 360, 1),
            "contrast_score": round(score, 1),
        })
        if len(candidates) >= max_candidates:
            break

    strongest = candidates[0]["contrast_score"] if candidates else 0.0
    return {
        "available": True,
        "sample_width": sample_width,
        "sample_height": sample_height,
        "confidence": "low",
        "interpretation": "heuristic_candidates_not_confirmed_stitching_defects",
        "strongest_score": strongest,
        "candidates": candidates,
    }
