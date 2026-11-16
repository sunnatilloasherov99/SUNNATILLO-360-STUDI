from collections.abc import Generator
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime, timezone
from PIL import Image
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import Base, Project, app, get_db


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    database = tmp_path / "studio-test.db"
    engine = create_engine(
        f"sqlite:///{database}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_session_factory = test_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.test_session_factory
        engine.dispose()


def register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SafePass-12345"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_registration_and_login(client: TestClient) -> None:
    token = register(client, "Owner@Example.com")
    me = client.get("/api/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"

    login = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "SafePass-12345"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    duplicate = client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "SafePass-12345"},
    )
    assert duplicate.status_code == 409


def test_project_and_media_routes_require_authentication(client: TestClient) -> None:
    response = client.post("/api/projects", json={"name": "Private project"})
    assert response.status_code == 401


def test_projects_and_editor_settings_are_private_to_owner(client: TestClient) -> None:
    owner_token = register(client, "owner@example.com")
    other_token = register(client, "other@example.com")

    created = client.post(
        "/api/projects",
        headers=bearer(owner_token),
        json={"name": "My private tour", "mode": "manual"},
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    empty_share = client.put(
        f"/api/projects/{project_id}/share",
        headers=bearer(owner_token),
        json={"enabled": True},
    )
    assert empty_share.status_code == 422

    owner_projects = client.get("/api/projects", headers=bearer(owner_token))
    other_projects = client.get("/api/projects", headers=bearer(other_token))
    assert len(owner_projects.json()) == 1
    assert other_projects.json() == []

    owner_settings = client.put(
        f"/api/projects/{project_id}/editor-settings",
        headers=bearer(owner_token),
        json={"brightness": 1.1, "contrast": 1.0, "saturation": 0.9},
    )
    assert owner_settings.status_code == 200

    other_settings = client.get(
        f"/api/projects/{project_id}/editor-settings",
        headers=bearer(other_token),
    )
    assert other_settings.status_code == 404

    other_media = client.get(
        f"/api/projects/{project_id}/media",
        headers=bearer(other_token),
    )
    assert other_media.status_code == 404


def test_tour_is_private_and_references_owned_media(client: TestClient) -> None:
    owner_token = register(client, "tour-owner@example.com")
    other_token = register(client, "tour-other@example.com")
    created = client.post(
        "/api/projects",
        headers=bearer(owner_token),
        json={"name": "Virtual tour", "mode": "manual"},
    )
    project_id = created.json()["id"]

    png_buffer = BytesIO()
    Image.new("RGB", (2, 1), color="white").save(png_buffer, format="PNG")
    uploaded = client.post(
        f"/api/projects/{project_id}/media",
        headers=bearer(owner_token),
        files={"file": ("entry.png", png_buffer.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 201
    media_id = uploaded.json()["id"]

    owner_ai_image = client.post(
        "/api/ai/assist",
        headers=bearer(owner_token),
        json={"role": "panorama_quality", "prompt": "Review this panorama", "media_id": media_id},
    )
    assert owner_ai_image.status_code == 503  # Image is valid; Ollama is intentionally not configured in CI.
    other_ai_image = client.post(
        "/api/ai/assist",
        headers=bearer(other_token),
        json={"role": "panorama_quality", "prompt": "Review this panorama", "media_id": media_id},
    )
    assert other_ai_image.status_code == 404

    video_upload = client.post(
        f"/api/projects/{project_id}/media",
        headers=bearer(owner_token),
        files={"file": ("walkthrough.mp4", b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2", "video/mp4")},
    )
    assert video_upload.status_code == 201
    assert video_upload.json()["contentType"] == "video/mp4"

    tour = {
        "title": "My 360 tour",
        "description": "A short walkthrough",
        "scenes": [
            {
                "id": "scene-entry",
                "media_id": media_id,
                "title": "Entry",
                "description": "Start here",
                "hotspots": [],
            }
        ],
    }
    saved = client.put(
        f"/api/projects/{project_id}/tour",
        headers=bearer(owner_token),
        json=tour,
    )
    assert saved.status_code == 200
    assert saved.json()["scenes"][0]["media_id"] == media_id

    quality = client.get(
        f"/api/projects/{project_id}/quality",
        headers=bearer(owner_token),
    )
    assert quality.status_code == 200
    assert quality.json()["summary"]["warning"] >= 1
    assert quality.json()["summary"]["fail"] == 0

    private_read = client.get(
        f"/api/projects/{project_id}/tour",
        headers=bearer(other_token),
    )
    assert private_read.status_code == 404

    invalid_tour = {
        **tour,
        "scenes": [{**tour["scenes"][0], "media_id": "not-owned-media"}],
    }
    invalid_save = client.put(
        f"/api/projects/{project_id}/tour",
        headers=bearer(owner_token),
        json=invalid_tour,
    )
    assert invalid_save.status_code == 422

    other_share = client.get(f"/api/projects/{project_id}/share", headers=bearer(other_token))
    assert other_share.status_code == 404
    enabled = client.put(
        f"/api/projects/{project_id}/share",
        headers=bearer(owner_token),
        json={"enabled": True},
    )
    assert enabled.status_code == 200
    share_path = enabled.json()["share_url"]
    share_token = share_path.rsplit("/", 1)[-1]
    public_tour = client.get(f"/api/public/tours/{share_token}")
    assert public_tour.status_code == 200
    assert public_tour.json()["scenes"][0]["title"] == "Entry"
    public_media = client.get(public_tour.json()["scenes"][0]["media_url"])
    assert public_media.status_code == 200
    assert public_media.headers["content-type"] == "image/png"

    disabled = client.put(
        f"/api/projects/{project_id}/share",
        headers=bearer(owner_token),
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert client.get(f"/api/public/tours/{share_token}").status_code == 404

    exported = client.get(
        f"/api/projects/{project_id}/export",
        headers=bearer(owner_token),
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(exported.content)) as archive:
        names = archive.namelist()
        assert "project.json" in names
        assert "tour.json" in names
        assert any(name.startswith("media/") for name in names)

    private_export = client.get(
        f"/api/projects/{project_id}/export",
        headers=bearer(other_token),
    )
    assert private_export.status_code == 404


def test_local_ai_is_opt_in_and_requires_authentication(client: TestClient) -> None:
    unauthenticated = client.get("/api/ai/capabilities")
    assert unauthenticated.status_code == 401

    token = register(client, "ai-user@example.com")
    capabilities = client.get("/api/ai/capabilities", headers=bearer(token))
    assert capabilities.status_code == 200
    assert capabilities.json()["providers"][0]["id"] == "ollama"
    assert capabilities.json()["providers"][0]["configured"] is False

    unavailable = client.post(
        "/api/ai/assist",
        headers=bearer(token),
        json={"role": "tour_planner", "prompt": "Plan a small tour", "language": "en"},
    )
    assert unavailable.status_code == 503


def test_login_rate_limit_returns_429(client: TestClient) -> None:
    headers = {"X-Real-IP": "198.51.100.77"}
    payload = {"email": "nobody@example.com", "password": "wrong-password"}
    for _ in range(10):
        response = client.post("/api/auth/login", headers=headers, json=payload)
        assert response.status_code == 401
    limited = client.post("/api/auth/login", headers=headers, json=payload)
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"


def test_first_registered_user_adopts_legacy_projects(client: TestClient) -> None:
    session = app.state.test_session_factory()
    now = datetime.now(timezone.utc)
    session.add(
        Project(
            id="legacy-project-0001",
            owner_id=None,
            name="Old project",
            mode="manual",
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
    session.close()

    token = register(client, "first-user@example.com")
    projects = client.get("/api/projects", headers=bearer(token))
    assert projects.status_code == 200
    assert [project["name"] for project in projects.json()] == ["Old project"]


def test_health_checks_database_and_media_storage(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["dependencies"]["database"] == "ok"
    assert response.json()["dependencies"]["media_storage"] == "ok"
