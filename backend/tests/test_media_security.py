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
