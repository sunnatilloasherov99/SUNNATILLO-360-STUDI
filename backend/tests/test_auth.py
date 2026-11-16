from collections.abc import Generator
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import Base, app, get_db


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
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SafePass-12345"},
    )
    assert response.status_code == 201
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

    uploaded = client.post(
        f"/api/projects/{project_id}/media",
        headers=bearer(owner_token),
        files={"file": ("entry.png", b"\x89PNG\r\n\x1a\nmock-image", "image/png")},
    )
    assert uploaded.status_code == 201
    media_id = uploaded.json()["id"]

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
