from __future__ import annotations

import os
import uuid
import hashlib
import secrets
import json
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from PIL import Image, UnidentifiedImageError
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Generator, Literal

from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
import jwt
import httpx


class Settings(BaseSettings):
    app_name: str = "SUNNATILLO 360° STUDIO API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./studio.db"
    media_storage_path: str = "./data/media"
    max_upload_mb: int = 100
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION"
    token_expire_hours: int = 24
    ollama_base_url: str = ""
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: int = 120
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
if settings.environment.lower() == "production" and (settings.jwt_secret == "CHANGE-ME-IN-PRODUCTION" or len(settings.jwt_secret) < 32):
    raise RuntimeError("Set a unique JWT_SECRET of at least 32 characters before running in production.")
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
    tour_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
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
    if "tour_json" not in columns:
        connection.execute(text("ALTER TABLE projects ADD COLUMN tour_json TEXT NOT NULL DEFAULT '{}'"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_owner_id ON projects (owner_id)"))

app = FastAPI(title=settings.app_name, version="0.2.0")
origins = [item.strip() for item in settings.frontend_origin.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
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


class AIRequest(BaseModel):
    role: Literal["panorama_quality", "tour_planner", "tour_description", "stitching_advisor"]
    prompt: str = Field(min_length=1, max_length=4000)
    context: str = Field(default="", max_length=10000)
    language: Literal["uz", "ru", "en"] = "uz"


AI_ROLE_PROMPTS = {
    "panorama_quality": "Act as a professional 360 panorama quality analyst. Review the user's supplied details, identify likely capture or stitching defects, explain confidence and give practical repair steps. Never claim to inspect an image unless image data was actually supplied.",
    "tour_planner": "Act as a virtual-tour experience designer. Organize spaces into a clear visitor journey, recommend scene order and useful hotspot connections. Be specific and practical.",
    "tour_description": "Act as a professional location and hospitality copywriter. Write accurate, clear descriptions for virtual-tour scenes. Do not invent amenities, measurements or business facts.",
    "stitching_advisor": "Act as a 360 photo stitching specialist. Diagnose seams, parallax, exposure mismatch and alignment issues from the user's description. Recommend safe edits while preserving the original source.",
}


class TourHotspotInput(BaseModel):
    target_scene_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=120)
    yaw: float = Field(default=0, ge=-6.28319, le=6.28319)
    pitch: float = Field(default=0, ge=-1.5708, le=1.5708)


class TourSceneInput(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    media_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    hotspots: list[TourHotspotInput] = Field(default_factory=list, max_length=20)


class TourPayload(BaseModel):
    title: str = Field(default="360° virtual tour", min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    scenes: list[TourSceneInput] = Field(default_factory=list, max_length=30)


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
        "ai_providers": [{"id": "ollama", "name": "Ollama local", "configured": bool(settings.ollama_base_url), "model": settings.ollama_model}],
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


@app.get("/api/projects/{project_id}/tour")
def get_project_tour(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return json.loads(project.tour_json or "{}")
    except json.JSONDecodeError:
        return {"title": project.name, "description": "", "scenes": []}


@app.put("/api/projects/{project_id}/tour")
def save_project_tour(project_id: str, payload: TourPayload, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    scene_ids = [scene.id for scene in payload.scenes]
    if len(scene_ids) != len(set(scene_ids)):
        raise HTTPException(status_code=422, detail="Tour scene IDs must be unique.")
    known_scenes = set(scene_ids)
    for scene in payload.scenes:
        if any(hotspot.target_scene_id not in known_scenes for hotspot in scene.hotspots):
            raise HTTPException(status_code=422, detail="Every hotspot must link to a scene in this tour.")
    media_ids = {scene.media_id for scene in payload.scenes}
    if media_ids:
        owned_assets = db.scalars(
            select(MediaAsset).join(Project).where(
                MediaAsset.id.in_(media_ids), Project.id == project_id, Project.owner_id == user.id,
                MediaAsset.content_type.like("image/%")
            )
        ).all()
        if {asset.id for asset in owned_assets} != media_ids:
            raise HTTPException(status_code=422, detail="A tour scene references media that is not in this project.")
    project.tour_json = payload.model_dump_json()
    project.updated_at = now_utc()
    db.commit()
    return payload.model_dump()


@app.get("/api/ai/capabilities")
def ai_capabilities(user: User = Depends(current_user)):
    return {
        "providers": [{"id": "ollama", "name": "Ollama (local)", "configured": bool(settings.ollama_base_url), "model": settings.ollama_model}],
        "roles": list(AI_ROLE_PROMPTS.keys()),
        "external_data_sent": False,
    }


@app.post("/api/ai/assist")
async def ai_assist(payload: AIRequest, user: User = Depends(current_user)):
    if not settings.ollama_base_url.strip():
        raise HTTPException(
            status_code=503,
            detail="Local AI is not configured. Install Ollama and set OLLAMA_BASE_URL in the server environment.",
        )
    language_names = {"uz": "Uzbek", "ru": "Russian", "en": "English"}
    system_prompt = (
        f"{AI_ROLE_PROMPTS[payload.role]} "
        f"Respond in {language_names[payload.language]}. "
        "Be honest about uncertainty. Do not fabricate visual observations or platform publishing permissions."
    )
    user_content = payload.prompt.strip()
    if payload.context.strip():
        user_content += "\n\nUser-provided context (only this text was shared):\n" + payload.context.strip()
    url = settings.ollama_base_url.rstrip("/") + "/api/chat"
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.post(
                url,
                json={
                    "model": settings.ollama_model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                },
            )
            response.raise_for_status()
            result = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="The local AI model took too long to respond.")
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="The local AI service returned an error.")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Could not connect to the local Ollama service.")
    output = result.get("message", {}).get("content", "").strip()
    if not output:
        raise HTTPException(status_code=502, detail="The local AI service returned an empty response.")
    return {"provider": "ollama", "model": settings.ollama_model, "role": payload.role, "output": output}


@app.get("/api/projects/{project_id}/quality")
def check_project_quality(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    assets = db.scalars(select(MediaAsset).where(MediaAsset.project_id == project_id)).all()
    checks = []
    valid_media_ids = set()
    for asset in assets:
        if asset.content_type.startswith("video/"):
            checks.append({"id": f"media-{asset.id}-video", "status": "warning", "message": f"{asset.original_name}: video quality analysis is not available yet."})
            continue
        path = storage_dir / asset.stored_name
        if not path.is_file():
            checks.append({"id": f"media-{asset.id}-file", "status": "fail", "message": f"Missing original file: {asset.original_name}"})
            continue
        try:
            with Image.open(path) as image:
                width, height = image.size
                image.verify()
            with Image.open(path) as image:
                image_format = image.format
            valid_media_ids.add(asset.id)
        except (UnidentifiedImageError, OSError, ValueError):
            checks.append({"id": f"media-{asset.id}-decode", "status": "fail", "message": f"Image cannot be decoded: {asset.original_name}"})
            continue
        checks.append({
            "id": f"media-{asset.id}-ratio",
            "status": "pass" if abs(width / height - 2) < 0.02 else "warning",
            "message": f"{asset.original_name}: {width}×{height}, aspect ratio {width / height:.2f}:1",
        })
        checks.append({
            "id": f"media-{asset.id}-resolution",
            "status": "pass" if width >= 4000 else "warning",
            "message": f"{asset.original_name}: {'recommended width met' if width >= 4000 else 'below recommended 4000 px width'}",
        })
        checks.append({
            "id": f"media-{asset.id}-format",
            "status": "pass" if image_format in {"JPEG", "PNG", "WEBP"} else "warning",
            "message": f"{asset.original_name}: {image_format or 'unknown'}",
        })
    if not assets:
        checks.append({"id": "media-present", "status": "warning", "message": "No panorama images have been uploaded yet."})
    try:
        tour = json.loads(project.tour_json or "{}")
    except json.JSONDecodeError:
        tour = {"scenes": []}
        checks.append({"id": "tour-json", "status": "fail", "message": "Tour configuration could not be read."})
    scenes = tour.get("scenes", []) if isinstance(tour, dict) else []
    if not scenes:
        checks.append({"id": "tour-scenes", "status": "warning", "message": "The virtual tour has no scenes yet."})
    else:
        checks.append({"id": "tour-scenes", "status": "pass", "message": f"Virtual tour contains {len(scenes)} scene(s)."})
        scene_ids = {scene.get("id") for scene in scenes if isinstance(scene, dict)}
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            if scene.get("media_id") not in valid_media_ids:
                checks.append({"id": f"scene-{scene.get('id', 'unknown')}-media", "status": "fail", "message": f"Scene '{scene.get('title', 'Untitled')}' has missing or invalid media."})
            for hotspot in scene.get("hotspots", []):
                if hotspot.get("target_scene_id") not in scene_ids:
                    checks.append({"id": f"scene-{scene.get('id', 'unknown')}-hotspot", "status": "fail", "message": f"Scene '{scene.get('title', 'Untitled')}' has a broken hotspot link."})
    summary = {status: sum(1 for check in checks if check["status"] == status) for status in ("pass", "warning", "fail")}
    return {"project_id": project.id, "project_name": project.name, "summary": summary, "checks": checks}


@app.get("/api/projects/{project_id}/export")
def export_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    assets = db.scalars(
        select(MediaAsset).where(MediaAsset.project_id == project_id).order_by(MediaAsset.created_at.asc())
    ).all()
    archive_buffer = BytesIO()
    with ZipFile(archive_buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps(project_data(project), ensure_ascii=False, indent=2))
        archive.writestr("editor-settings.json", project.edit_settings_json or "{}")
        archive.writestr("tour.json", project.tour_json or "{}")
        missing_files = []
        for asset in assets:
            source = storage_dir / asset.stored_name
            if not source.is_file():
                missing_files.append(asset.id)
                continue
            safe_name = (asset.original_name or "media").replace(chr(92), "/").split("/")[-1]
            archive.write(source, arcname=f"media/{asset.id}_{safe_name}")
        archive.writestr("export-manifest.json", json.dumps({
            "media_count": len(assets),
            "missing_media_ids": missing_files,
            "originals_included": len(assets) - len(missing_files),
        }, ensure_ascii=False, indent=2))
    filename = f"sunnatillo-360-{project_id}.zip"
    return Response(
        content=archive_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
        "video/mp4": ".mp4",
        "video/webm": ".webm",
    }
    extension = allowed_types.get(file.content_type or "")
    if not extension:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, WebP, MP4 and WebM media are supported.")

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
        "video/mp4": lambda data: len(data) >= 8 and data[4:8] == b"ftyp",
        "video/webm": lambda data: data.startswith(bytes([0x1A, 0x45, 0xDF, 0xA3])),
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
