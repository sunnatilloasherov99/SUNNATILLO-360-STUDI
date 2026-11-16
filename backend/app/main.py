from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, Depends, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session


class Settings(BaseSettings):
    app_name: str = "SUNNATILLO 360° STUDIO API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./studio.db"
    media_storage_path: str = "./data/media"
    max_upload_mb: int = 100
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
storage_dir = Path(settings.media_storage_path).resolve()
storage_dir.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    media: Mapped[list["MediaAsset"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    project: Mapped[Project] = relationship(back_populates="media")


Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="0.2.0")
origins = [item.strip() for item in settings.frontend_origin.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ProjectCreate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=160)
    mode: str = Field(default="manual", pattern="^(ai|manual|collab)$")


def project_data(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "mode": project.mode,
        "createdAt": project.created_at.isoformat(),
        "updatedAt": project.updated_at.isoformat(),
    }


def media_data(asset: MediaAsset) -> dict:
    return {
        "id": asset.id,
        "projectId": asset.project_id,
        "name": asset.original_name,
        "contentType": asset.content_type,
        "sizeBytes": asset.size_bytes,
        "createdAt": asset.created_at.isoformat(),
        "url": f"/api/media/{asset.id}/file",
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "application": "SUNNATILLO 360° STUDIO", "version": "0.2.0"}


@app.get("/api/capabilities")
async def capabilities():
    return {
        "server_projects": True,
        "persistent_media": True,
        "max_upload_mb": settings.max_upload_mb,
        "ai_providers": [],
        "publishing_targets": [],
        "note": "External providers are opt-in and must be configured server-side."
    }


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.updated_at.desc())).all()
    return [project_data(project) for project in projects]


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.id):
        raise HTTPException(status_code=409, detail="A project with this ID already exists.")
    project = Project(
        id=payload.id,
        name=payload.name.strip(),
        mode=payload.mode,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    if not project.name:
        raise HTTPException(status_code=422, detail="Project name cannot be empty.")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project_data(project)


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    stored_names = [asset.stored_name for asset in project.media]
    db.delete(project)
    db.commit()
    for stored_name in stored_names:
        (storage_dir / stored_name).unlink(missing_ok=True)
    return None


@app.get("/api/projects/{project_id}/media")
def list_project_media(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    assets = db.scalars(
        select(MediaAsset).where(MediaAsset.project_id == project_id).order_by(MediaAsset.created_at.desc())
    ).all()
    return [media_data(asset) for asset in assets]


@app.post("/api/projects/{project_id}/media", status_code=201)
async def upload_project_media(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    extension = allowed_types.get(file.content_type or "")
    if not extension:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG and WebP images are supported.")

    asset_id = str(uuid.uuid4())
    stored_name = f"{asset_id}{extension}"
    destination = storage_dir / stored_name
    total = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(status_code=413, detail=f"File exceeds the {settings.max_upload_mb} MB limit.")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if total == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    asset = MediaAsset(
        id=asset_id,
        project_id=project_id,
        original_name=Path(file.filename or f"panorama{extension}").name[:255],
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=total,
        created_at=now_utc(),
    )
    project.updated_at = now_utc()
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return media_data(asset)


@app.get("/api/media/{asset_id}/file")
def get_media_file(asset_id: str, db: Session = Depends(get_db)):
    asset = db.get(MediaAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Media file not found.")
    path = storage_dir / asset.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored media file is missing.")
    return FileResponse(path, media_type=asset.content_type, filename=asset.original_name)
