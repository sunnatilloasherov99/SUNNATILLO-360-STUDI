from __future__ import annotations

import os
import uuid
import hashlib
import secrets
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
import jwt


class Settings(BaseSettings):
    app_name: str = "SUNNATILLO 360° STUDIO API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./studio.db"
    media_storage_path: str = "./data/media"
    max_upload_mb: int = 100
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION"
    token_expire_hours: int = 24
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
if settings.environment.lower() == "production" and settings.jwt_secret == "CHANGE-ME-IN-PRODUCTION":
    raise RuntimeError("Set a unique JWT_SECRET before running in production.")
storage_dir = Path(settings.media_storage_path).resolve()
storage_dir.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    edit_settings_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
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
# Upgrade existing development databases without losing projects.
with engine.begin() as connection:
    columns = {column["name"] for column in inspect(engine).get_columns("projects")}
    if "owner_id" not in columns:
        connection.execute(text("ALTER TABLE projects ADD COLUMN owner_id VARCHAR(36)"))
    if "edit_settings_json" not in columns:
        connection.execute(text("ALTER TABLE projects ADD COLUMN edit_settings_json TEXT NOT NULL DEFAULT '{}'"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_owner_id ON projects (owner_id)"))

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


class RegisterPayload(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginPayload(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 310000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
        actual = hash_password(password, salt).split("$", 1)[1]
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_token(user: User) -> str:
    return jwt.encode({"sub": user.id, "exp": now_utc() + timedelta(hours=settings.token_expire_hours)}, settings.jwt_secret, algorithm="HS256")


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi.")
    token = authorization[7:].strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user = db.get(User, payload.get("sub"))
    except jwt.PyJWTError:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Kirish muddati tugagan yoki token noto‘g‘ri.")
    return user


class EditorSettings(BaseModel):
    brightness: float = Field(default=1.0, ge=0.5, le=1.5)
    contrast: float = Field(default=1.0, ge=0.5, le=1.5)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)


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


@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterPayload, db: Session = Depends(get_db)):
    email = normalize_email(payload.email)
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Email manzilini to‘g‘ri kiriting.")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Bu email bilan hisob mavjud.")
    user = User(id=str(uuid.uuid4()), email=email, password_hash=hash_password(payload.password), created_at=now_utc())
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": issue_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email}}


@app.post("/api/auth/login")
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email yoki parol noto‘g‘ri.")
    return {"access_token": issue_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email}}


@app.get("/api/auth/me")
def who_am_i(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}


@app.get("/api/projects")
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.updated_at.desc())).all()
    return [project_data(project) for project in projects]


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.get(Project, payload.id):
        raise HTTPException(status_code=409, detail="A project with this ID already exists.")
    project = Project(
        id=payload.id,
        owner_id=user.id,
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


@app.get("/api/projects/{project_id}/editor-settings")
def get_editor_settings(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return json.loads(project.edit_settings_json or "{}")
    except json.JSONDecodeError:
        return {"brightness": 1.0, "contrast": 1.0, "saturation": 1.0}


@app.put("/api/projects/{project_id}/editor-settings")
def save_editor_settings(project_id: str, payload: EditorSettings, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    project.edit_settings_json = payload.model_dump_json()
    project.updated_at = now_utc()
    db.commit()
    return payload.model_dump()


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    stored_names = [asset.stored_name for asset in project.media]
    db.delete(project)
    db.commit()
    for stored_name in stored_names:
        (storage_dir / stored_name).unlink(missing_ok=True)
    return None


@app.get("/api/projects/{project_id}/media")
def list_project_media(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id)):
        raise HTTPException(status_code=404, detail="Project not found.")
    assets = db.scalars(
        select(MediaAsset).where(MediaAsset.project_id == project_id).order_by(MediaAsset.created_at.desc())
    ).all()
    return [media_data(asset) for asset in assets]


@app.post("/api/projects/{project_id}/media", status_code=201)
async def upload_project_media(
    project_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
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
    header = bytearray()
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(status_code=413, detail=f"File exceeds the {settings.max_upload_mb} MB limit.")
                if len(header) < 12:
                    header.extend(chunk[: 12 - len(header)])
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if total == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    signatures = {
        "image/jpeg": lambda data: data.startswith(bytes([255, 216, 255])),
        "image/png": lambda data: data.startswith(bytes([137, 80, 78, 71, 13, 10, 26, 10])),
        "image/webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }
    if not signatures[file.content_type or ""](bytes(header)):
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail="The file content does not match its declared image type.")

    safe_original_name = (file.filename or f"panorama{extension}").replace(chr(92), "/").split("/")[-1][:255]
    asset = MediaAsset(
        id=asset_id,
        project_id=project_id,
        original_name=safe_original_name,
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
def get_media_file(asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    asset = db.scalar(select(MediaAsset).join(Project).where(MediaAsset.id == asset_id, Project.owner_id == user.id))
    if not asset:
        raise HTTPException(status_code=404, detail="Media file not found.")
    path = storage_dir / asset.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored media file is missing.")
    return FileResponse(path, media_type=asset.content_type, headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff"})
