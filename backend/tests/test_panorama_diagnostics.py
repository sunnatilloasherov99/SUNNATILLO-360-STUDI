from PIL import Image, ImageDraw

from app.panorama_diagnostics import find_vertical_discontinuities


def test_finds_synthetic_vertical_discontinuity():
    image = Image.new("RGB", (200, 100), (100, 100, 100))
    draw = ImageDraw.Draw(image)
    draw.rectangle((99, 0, 101, 99), fill=(255, 255, 255))

    result = find_vertical_discontinuities(image)

    assert result["available"] is True
    assert result["confidence"] == "low"
    assert result["interpretation"] == "heuristic_candidates_not_confirmed_stitching_defects"
    assert result["candidates"]
    assert abs(result["candidates"][0]["position"] - 0.5) < 0.08


def test_reports_wrap_boundary_candidate():
    image = Image.new("RGB", (200, 100), (100, 100, 100))
    pixels = image.load()
    for y in range(100):
        pixels[0, y] = (255, 255, 255)
        pixels[199, y] = (0, 0, 0)

    result = find_vertical_discontinuities(image)

    assert result["available"] is True
    assert any(candidate["x_px"] in (0, 1, 199) for candidate in result["candidates"])


def test_skips_non_equirectangular_images():
    result = find_vertical_discontinuities(Image.new("RGB", (120, 90), "gray"))

    assert result["available"] is False
    assert result["reason"] == "not_equirectangular"
    assert result["candidates"] == []
