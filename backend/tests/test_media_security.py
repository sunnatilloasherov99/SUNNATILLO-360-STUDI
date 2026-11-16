from collections.abc import Generator
from io import BytesIO
from pathlib import Path
import sys

from PIL import Image
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main as main


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    database = tmp_path / "media-security.db"
    engine = create_engine(
        f"sqlite:///{database}",
        connect_args={"check_same_thread": False},
    )
    main.Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    media_dir = tmp_path / "media"
    media_dir.mkdir()
    monkeypatch.setattr(main, "storage_dir", media_dir)
    monkeypatch.setattr(main.settings, "max_upload_mb", 1)
    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        headers={"X-Real-IP": f"test-{email}"},
        json={"email": email, "password": "SafePass-12345"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def create_project(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Media security test", "mode": "manual"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 2), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_rejects_mismatched_file_signature(client: TestClient) -> None:
    token = register(client, "signature@example.com")
    project_id = create_project(client, token)

    response = client.post(
        f"/api/projects/{project_id}/media",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("fake.png", b"this is not a PNG", "image/png")},
    )

    assert response.status_code == 415
    assert list(main.storage_dir.iterdir()) == []


def test_media_file_is_only_available_to_project_owner(client: TestClient) -> None:
    owner_token = register(client, "media-owner@example.com")
    other_token = register(client, "media-other@example.com")
    project_id = create_project(client, owner_token)

    uploaded = client.post(
        f"/api/projects/{project_id}/media",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("panorama.png", png_bytes(), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    media_id = uploaded.json()["id"]

    owner_read = client.get(
        f"/api/media/{media_id}/file",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_read.status_code == 200
    assert owner_read.headers["x-content-type-options"] == "nosniff"

    other_read = client.get(
        f"/api/media/{media_id}/file",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_read.status_code == 404


def test_upload_limit_is_enforced_and_partial_file_removed(client: TestClient) -> None:
    token = register(client, "size@example.com")
    project_id = create_project(client, token)
    oversized = b"\x89PNG\r\n\x1a\n" + b"x" * (1024 * 1024)

    response = client.post(
        f"/api/projects/{project_id}/media",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("large.png", oversized, "image/png")},
    )

    assert response.status_code == 413
    assert list(main.storage_dir.iterdir()) == []


def upload_png(client: TestClient, token: str, project_id: str) -> str:
    response = client.post(
        f"/api/projects/{project_id}/media",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("tour-scene.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_editor_settings_validate_and_persist_seam_blend(client: TestClient) -> None:
    owner_token = register(client, "seam-blend-owner@example.com")
    other_token = register(client, "seam-blend-other@example.com")
    project_id = create_project(client, owner_token)
    url = f"/api/projects/{project_id}/editor-settings"
    headers = {"Authorization": f"Bearer {owner_token}"}

    saved = client.put(
        url,
        headers=headers,
        json={"brightness": 1.1, "contrast": 1.0, "saturation": 1.0, "seam_offset": 25, "seam_blend_percent": 3.5},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["seam_blend_percent"] == 3.5
    assert client.get(url, headers=headers).json()["seam_blend_percent"] == 3.5
    assert client.get(
        url,
        headers={"Authorization": f"Bearer {other_token}"},
    ).status_code == 404

    invalid = client.put(
        url,
        headers=headers,
        json={"seam_blend_percent": 5.1},
    )
    assert invalid.status_code == 422


def test_quality_report_estimates_seam_continuity_and_is_private(client: TestClient) -> None:
    owner_token = register(client, "seam-quality-owner@example.com")
    other_token = register(client, "seam-quality-other@example.com")
    project_id = create_project(client, owner_token)
    headers = {"Authorization": f"Bearer {owner_token}"}

    image = Image.new("RGB", (32, 16), color=(120, 120, 120))
    pixels = image.load()
    for y in range(image.height):
        pixels[0, y] = (0, 0, 0)
        pixels[image.width - 1, y] = (255, 255, 255)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    uploaded = client.post(
        f"/api/projects/{project_id}/media",
        headers=headers,
        files={"file": ("seam-defect.png", buffer.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text

    quality_url = f"/api/projects/{project_id}/quality"
    assert client.get(
        quality_url,
        headers={"Authorization": f"Bearer {other_token}"},
    ).status_code == 404

    report = client.get(quality_url, headers=headers)
    assert report.status_code == 200, report.text
    seam_check = next(
        check for check in report.json()["checks"]
        if check["code"] == "seam_continuity"
    )
    assert seam_check["status"] == "warning"
    assert seam_check["params"]["level"] == "high"
    assert seam_check["params"]["score"] >= 45


def test_tour_rejects_hotspots_that_point_to_unknown_scenes(client: TestClient) -> None:
    token = register(client, "tour-validation@example.com")
    project_id = create_project(client, token)
    media_id = upload_png(client, token, project_id)

    response = client.put(
        f"/api/projects/{project_id}/tour",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test tour",
            "scenes": [
                {
                    "id": "lobby",
                    "media_id": media_id,
                    "title": "Lobby",
                    "hotspots": [
                        {
                            "target_scene_id": "missing-room",
                            "title": "Go to missing room",
                        }
                    ],
                }
            ],
        },
    )

    assert response.status_code == 422
    assert "hotspot" in response.json()["detail"].lower()


def test_public_tour_link_can_be_revoked(client: TestClient) -> None:
    token = register(client, "tour-sharing@example.com")
    project_id = create_project(client, token)
    media_id = upload_png(client, token, project_id)
    headers = {"Authorization": f"Bearer {token}"}

    saved_tour = client.put(
        f"/api/projects/{project_id}/tour",
        headers=headers,
        json={
            "title": "Public test tour",
            "description": "A test virtual tour",
            "scenes": [
                {
                    "id": "entrance",
                    "media_id": media_id,
                    "title": "Entrance",
                    "description": "Main entrance",
                    "hotspots": [],
                }
            ],
        },
    )
    assert saved_tour.status_code == 200, saved_tour.text

    enabled = client.put(
        f"/api/projects/{project_id}/share",
        headers=headers,
        json={"enabled": True},
    )
    assert enabled.status_code == 200
    share_url = enabled.json()["share_url"]
    share_token = share_url.rsplit("/", 1)[-1]

    public_tour = client.get(f"/api/public/tours/{share_token}")
    assert public_tour.status_code == 200
    assert len(public_tour.json()["scenes"]) == 1

    revoked = client.put(
        f"/api/projects/{project_id}/share",
        headers=headers,
        json={"enabled": False},
    )
    assert revoked.status_code == 200
    assert revoked.json()["enabled"] is False
    assert client.get(f"/api/public/tours/{share_token}").status_code == 404
    assert client.get(
        f"/api/public/media/{share_token}/{media_id}"
    ).status_code == 404




def test_ai_video_analysis_requires_ffmpeg_and_respects_project_ownership(client: TestClient, monkeypatch) -> None:
    owner_token = register(client, "ai-video-owner@example.com")
    other_token = register(client, "ai-video-other@example.com")
    project_id = create_project(client, owner_token)
    uploaded = client.post(
        f"/api/projects/{project_id}/media",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("walkthrough.mp4", b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2", "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    media_id = uploaded.json()["id"]
    payload = {"role": "panorama_quality", "prompt": "Review this 360 video", "media_id": media_id}

    private = client.post(
        "/api/ai/assist",
        headers={"Authorization": f"Bearer {other_token}"},
        json=payload,
    )
    assert private.status_code == 404

    monkeypatch.setattr(main.shutil, "which", lambda _name: None)
    unavailable = client.post(
        "/api/ai/assist",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=payload,
    )
    assert unavailable.status_code == 503
    assert "FFmpeg" in unavailable.json()["detail"]



def test_video_export_is_private_and_requires_ffmpeg(client: TestClient, monkeypatch) -> None:
    owner_token = register(client, "video-export-owner@example.com")
    other_token = register(client, "video-export-other@example.com")
    project_id = create_project(client, owner_token)
    headers = {"Authorization": f"Bearer {owner_token}"}
    uploaded = client.post(
        f"/api/projects/{project_id}/media",
        headers=headers,
        files={"file": ("walkthrough.mp4", b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2", "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    media_id = uploaded.json()["id"]

    export_url = f"/api/projects/{project_id}/video-export"
    assert client.post(
        export_url,
        headers={"Authorization": f"Bearer {other_token}"},
        json={"media_id": media_id},
    ).status_code == 404

    monkeypatch.setattr(main.shutil, "which", lambda _name: None)
    unavailable = client.post(export_url, headers=headers, json={"media_id": media_id})
    assert unavailable.status_code == 503
    assert "FFmpeg" in unavailable.json()["detail"]


def test_video_export_rejects_image_assets(client: TestClient, monkeypatch) -> None:
    token = register(client, "video-export-image@example.com")
    project_id = create_project(client, token)
    media_id = upload_png(client, token, project_id)
    monkeypatch.setattr(main.shutil, "which", lambda _name: "/usr/bin/ffmpeg")
    response = client.post(
        f"/api/projects/{project_id}/video-export",
        headers={"Authorization": f"Bearer {token}"},
        json={"media_id": media_id},
    )
    assert response.status_code == 404


def test_video_trim_settings_are_private_validated_and_persisted(client: TestClient) -> None:
    owner_token = register(client, "video-settings-owner@example.com")
    other_token = register(client, "video-settings-other@example.com")
    project_id = create_project(client, owner_token)
    url = f"/api/projects/{project_id}/video-settings"
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    assert client.get(url, headers=other_headers).status_code == 404
    saved = client.put(
        url,
        headers=owner_headers,
        json={"start_seconds": 5.5, "end_seconds": 42.0},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"start_seconds": 5.5, "end_seconds": 42.0}
    assert client.get(url, headers=owner_headers).json() == saved.json()

    invalid = client.put(
        url,
        headers=owner_headers,
        json={"start_seconds": 30, "end_seconds": 20},
    )
    assert invalid.status_code == 422
    assert client.get(url, headers=owner_headers).json() == saved.json()
