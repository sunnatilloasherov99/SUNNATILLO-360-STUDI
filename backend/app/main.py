import os
import asyncio
from collections import deque
from time import monotonic
import uuid
import hashlib
import secrets
import json
import base64
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from PIL import Image, UnidentifiedImageError
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Generator, Literal

from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
import jwt
import httpx
from redis.asyncio import Redis
from redis.exceptions import RedisError


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
    rate_limit_storage_uri: str = "memory://"
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
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
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


app = FastAPI(title=settings.app_name, version="0.2.0")


@app.middleware("http")
async def prevent_api_response_caching(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response
rate_limit_redis = (
    Redis.from_url(settings.rate_limit_storage_uri, decode_responses=True)
    if settings.rate_limit_storage_uri.startswith(("redis://", "rediss://"))
    else None
)
_rate_limit_events: dict[str, deque[float]] = {}
_rate_limit_lock = asyncio.Lock()
ai_semaphore = asyncio.Semaphore(2)
origins = [item.strip() for item in settings.frontend_origin.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_request_rate_limits(request: Request, call_next):
    limits = {
        ("POST", "/api/auth/register"): 10,
        ("POST", "/api/auth/login"): 10,
        ("POST", "/api/ai/assist"): 20,
    }
    limit = limits.get((request.method, request.url.path))
    if request.method == "GET" and request.url.path.startswith("/api/public/tours/"):
        limit = 60
    elif request.method == "GET" and request.url.path.startswith("/api/public/media/"):
        limit = 120
    if limit is None:
        return await call_next(request)

    # X-Real-IP is set by the private Nginx reverse proxy in Docker deployments.
    client_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    key = f"s360:rate:{client_ip}:{request.url.path}"
    count = None
    if rate_limit_redis is not None:
        try:
            count = await rate_limit_redis.eval(
                "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n",
                1,
                key,
                60,
            )
        except RedisError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Rate limiting service is temporarily unavailable."},
                headers={"Retry-After": "30"},
            )

    if count is None:
        now = monotonic()
        async with _rate_limit_lock:
            events = _rate_limit_events.setdefault(key, deque())
            while events and events[0] <= now - 60:
                events.popleft()
            if len(events) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again in a minute."},
                    headers={"Retry-After": "60"},
                )
            events.append(now)
            count = len(events)

    if count > limit:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again in a minute."},
            headers={"Retry-After": "60"},
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(limit - count, 0))
    return response


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
    seam_offset: int = Field(default=0, ge=0, le=359)


class VideoTrimSettings(BaseModel):
    start_seconds: float = Field(default=0.0, ge=0.0, le=86400.0)
    end_seconds: float = Field(default=0.0, ge=0.0, le=86400.0)


class AIRequest(BaseModel):
    role: Literal["panorama_quality", "tour_planner", "tour_description", "stitching_advisor", "collaboration"]
    prompt: str = Field(min_length=1, max_length=4000)
    context: str = Field(default="", max_length=10000)
    language: Literal["uz", "ru", "en"] = "uz"
    media_id: str | None = Field(default=None, max_length=36)


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


class ShareUpdate(BaseModel):
    enabled: bool


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
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is unavailable.")
    if rate_limit_redis is not None:
        try:
            await rate_limit_redis.ping()
        except RedisError:
            raise HTTPException(status_code=503, detail="Rate limit storage is unavailable.")
    if not storage_dir.is_dir() or not os.access(storage_dir, os.W_OK):
        raise HTTPException(status_code=503, detail="Media storage is unavailable.")
    return {
        "status": "ok",
        "application": "SUNNATILLO 360° STUDIO",
        "version": "0.2.0",
        "dependencies": {"database": "ok", "rate_limit_storage": "ok" if rate_limit_redis else "memory", "media_storage": "ok"},
    }


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
    first_user = db.scalar(select(User.id).limit(1)) is None
    user = User(id=str(uuid.uuid4()), email=email, password_hash=hash_password(payload.password), created_at=now_utc())
    db.add(user)
    db.flush()
    if first_user:
        # Safely adopt projects created before accounts existed.
        db.execute(update(Project).where(Project.owner_id.is_(None)).values(owner_id=user.id))
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


@app.get("/api/projects/{project_id}/video-settings")
def get_video_settings(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        saved = json.loads(project.edit_settings_json or "{}").get("video", {})
    except (json.JSONDecodeError, AttributeError):
        saved = {}
    return VideoTrimSettings.model_validate(saved).model_dump()


@app.put("/api/projects/{project_id}/video-settings")
def save_video_settings(project_id: str, payload: VideoTrimSettings, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if payload.end_seconds and payload.end_seconds <= payload.start_seconds:
        raise HTTPException(status_code=422, detail="End time must be greater than start time.")
    try:
        saved = json.loads(project.edit_settings_json or "{}")
    except json.JSONDecodeError:
        saved = {}
    saved["video"] = payload.model_dump()
    project.edit_settings_json = json.dumps(saved)
    project.updated_at = now_utc()
    db.commit()
    return payload.model_dump()


@app.get("/api/projects/{project_id}/share")
def get_project_share(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {
        "enabled": bool(project.is_public and project.share_token),
        "share_url": f"/tour/{project.share_token}" if project.is_public and project.share_token else None,
    }


@app.put("/api/projects/{project_id}/share")
def update_project_share(project_id: str, payload: ShareUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if payload.enabled:
        try:
            saved_tour = json.loads(project.tour_json or "{}")
        except json.JSONDecodeError:
            saved_tour = {}
        if not saved_tour.get("scenes"):
            raise HTTPException(status_code=422, detail="Add at least one scene before enabling a public tour link.")
        project.share_token = project.share_token or uuid.uuid4().hex
        project.is_public = True
    else:
        project.is_public = False
        project.share_token = None
    db.commit()
    return {
        "enabled": bool(project.is_public and project.share_token),
        "share_url": f"/tour/{project.share_token}" if project.is_public and project.share_token else None,
    }


@app.get("/api/public/tours/{token}")
def get_public_tour(token: str, db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.share_token == token, Project.is_public.is_(True)))
    if not project:
        raise HTTPException(status_code=404, detail="Public tour not found.")
    try:
        tour = json.loads(project.tour_json or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=404, detail="Public tour is unavailable.")
    scenes = tour.get("scenes", []) if isinstance(tour, dict) else []
    media_ids = {scene.get("media_id") for scene in scenes if isinstance(scene, dict)}
    assets = db.scalars(
        select(MediaAsset).where(
            MediaAsset.project_id == project.id,
            MediaAsset.id.in_(media_ids) if media_ids else MediaAsset.id == "",
            MediaAsset.content_type.like("image/%"),
        )
    ).all()
    asset_ids = {asset.id for asset in assets}
    public_scenes = []
    for scene in scenes:
        if not isinstance(scene, dict) or scene.get("media_id") not in asset_ids:
            continue
        public_scenes.append({
            "id": scene.get("id"),
            "title": scene.get("title", ""),
            "description": scene.get("description", ""),
            "media_url": f"/api/public/media/{token}/{scene['media_id']}",
            "hotspots": scene.get("hotspots", []),
        })
    return {
        "project_name": project.name,
        "title": tour.get("title") or project.name,
        "description": tour.get("description", ""),
        "scenes": public_scenes,
    }


@app.get("/api/public/media/{token}/{asset_id}")
def get_public_media(token: str, asset_id: str, db: Session = Depends(get_db)):
    asset = db.scalar(
        select(MediaAsset).join(Project).where(
            MediaAsset.id == asset_id,
            Project.share_token == token,
            Project.is_public.is_(True),
            MediaAsset.content_type.like("image/%"),
        )
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Public media not found.")
    path = storage_dir / asset.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media file not found.")
    return FileResponse(
        path,
        media_type=asset.content_type,
        filename=asset.original_name,
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
    )


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
    if not payload.scenes and project.is_public:
        project.is_public = False
        project.share_token = None
    project.updated_at = now_utc()
    db.commit()
    return payload.model_dump()


@app.get("/api/ai/capabilities")
def ai_capabilities(user: User = Depends(current_user)):
    return {
        "providers": [{"id": "ollama", "name": "Ollama (local)", "configured": bool(settings.ollama_base_url), "model": settings.ollama_model}],
        "roles": [*AI_ROLE_PROMPTS.keys(), "collaboration"],
        "external_data_sent": False,
    }


@app.post("/api/ai/assist")
async def ai_assist(payload: AIRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    image_base64 = None
    if payload.media_id:
        asset = db.scalar(
            select(MediaAsset).join(Project).where(
                MediaAsset.id == payload.media_id,
                Project.owner_id == user.id,
                MediaAsset.content_type.like("image/%"),
            )
        )
        if not asset:
            raise HTTPException(status_code=404, detail="Selected image was not found in your projects.")
        image_path = storage_dir / asset.stored_name
        if not image_path.is_file():
            raise HTTPException(status_code=404, detail="Selected image file is missing.")
        if image_path.stat().st_size > 12 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Choose an image smaller than 12 MB for local AI analysis.")
        image_bytes = image_path.read_bytes()
        try:
            with Image.open(image_path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise HTTPException(status_code=422, detail="Selected image is invalid or cannot be decoded.")
        image_base64 = base64.b64encode(image_bytes).decode("ascii")
    if not settings.ollama_base_url.strip():
        raise HTTPException(
            status_code=503,
            detail="Local AI is not configured. Install Ollama and set OLLAMA_BASE_URL in the server environment.",
        )
    language_names = {"uz": "Uzbek", "ru": "Russian", "en": "English"}
    user_content = payload.prompt.strip()
    if payload.context.strip():
        user_content += "\n\nUser-provided context (only this text was shared):\n" + payload.context.strip()
    user_message = {
        "role": "user",
        "content": user_content + ("\n\nPlease inspect the attached image." if image_base64 else ""),
        **({"images": [image_base64]} if image_base64 else {}),
    }
    url = settings.ollama_base_url.rstrip("/") + "/api/chat"
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            if payload.role == "collaboration":
                team_roles = ["panorama_quality", "stitching_advisor", "tour_planner"]
                async def ask_specialist(role_name: str):
                    system = (
                        f"{AI_ROLE_PROMPTS[role_name]} "
                        f"Respond in {language_names[payload.language]}. "
                        "Be honest about uncertainty and never invent visual observations."
                    )
                    async with ai_semaphore:
                        response = await client.post(
                            url,
                            json={"model": settings.ollama_model, "stream": False, "messages": [
                                {"role": "system", "content": system}, user_message
                            ]},
                        )
                    response.raise_for_status()
                    content = response.json().get("message", {}).get("content", "").strip()
                    if not content:
                        raise HTTPException(status_code=502, detail="A local AI specialist returned an empty response.")
                    return content
                reports = await asyncio.gather(*(ask_specialist(role_name) for role_name in team_roles))
                headings = {
                    "uz": ["360° sifat mutaxassisi", "Stitching mutaxassisi", "Virtual tur rejissyori"],
                    "ru": ["Аналитик качества 360°", "Специалист по склейке", "Режиссёр виртуального тура"],
                    "en": ["360° quality analyst", "Stitching specialist", "Virtual tour planner"],
                }[payload.language]
                output = "\n\n".join(f"### {heading}\n{report}" for heading, report in zip(headings, reports))
            else:
                system_prompt = (
                    f"{AI_ROLE_PROMPTS[payload.role]} "
                    f"Respond in {language_names[payload.language]}. "
                    "Be honest about uncertainty. Do not fabricate visual observations or platform publishing permissions."
                )
                async with ai_semaphore:
                    response = await client.post(
                        url,
                        json={"model": settings.ollama_model, "stream": False, "messages": [
                            {"role": "system", "content": system_prompt}, user_message
                        ]},
                    )
                response.raise_for_status()
                output = response.json().get("message", {}).get("content", "").strip()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="The local AI model took too long to respond.")
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="The local AI service returned an error.")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Could not connect to the local Ollama service.")
    if not output:
        raise HTTPException(status_code=502, detail="The local AI service returned an empty response.")
    return {"provider": "ollama", "model": settings.ollama_model, "role": payload.role, "output": output, "image_analyzed": bool(image_base64)}



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
            checks.append({"id": f"media-{asset.id}-video", "code": "video_check_pending", "status": "warning", "params": {"name": asset.original_name}, "message": f"{asset.original_name}: video quality analysis is not available yet."})
            continue
        path = storage_dir / asset.stored_name
        if not path.is_file():
            checks.append({"id": f"media-{asset.id}-file", "code": "missing_file", "status": "fail", "params": {"name": asset.original_name}, "message": f"Missing original file: {asset.original_name}"})
            continue
        try:
            with Image.open(path) as image:
                width, height = image.size
                image.verify()
            with Image.open(path) as image:
                image_format = image.format
            valid_media_ids.add(asset.id)
        except (UnidentifiedImageError, OSError, ValueError):
            checks.append({"id": f"media-{asset.id}-decode", "code": "invalid_image", "status": "fail", "params": {"name": asset.original_name}, "message": f"Image cannot be decoded: {asset.original_name}"})
            continue
        checks.append({
            "id": f"media-{asset.id}-ratio",
            "code": "aspect_ratio",
            "status": "pass" if abs(width / height - 2) < 0.02 else "warning",
            "params": {"name": asset.original_name, "width": width, "height": height, "ratio": round(width / height, 2)},
            "message": f"{asset.original_name}: {width}×{height}, aspect ratio {width / height:.2f}:1",
        })
        checks.append({
            "id": f"media-{asset.id}-resolution",
            "code": "resolution",
            "status": "pass" if width >= 4000 else "warning",
            "params": {"name": asset.original_name, "width": width, "minimum_width": 4000},
            "message": f"{asset.original_name}: {'recommended width met' if width >= 4000 else 'below recommended 4000 px width'}",
        })
        checks.append({
            "id": f"media-{asset.id}-format",
            "code": "image_format",
            "status": "pass" if image_format in {"JPEG", "PNG", "WEBP"} else "warning",
            "params": {"name": asset.original_name, "format": image_format or "unknown"},
            "message": f"{asset.original_name}: {image_format or 'unknown'}",
        })
    if not assets:
        checks.append({"id": "media-present", "code": "no_media", "status": "warning", "params": {}, "message": "No panorama images have been uploaded yet."})
    try:
        tour = json.loads(project.tour_json or "{}")
    except json.JSONDecodeError:
        tour = {"scenes": []}
        checks.append({"id": "tour-json", "code": "invalid_tour_json", "status": "fail", "params": {}, "message": "Tour configuration could not be read."})
    scenes = tour.get("scenes", []) if isinstance(tour, dict) else []
    if not scenes:
        checks.append({"id": "tour-scenes", "code": "no_tour_scenes", "status": "warning", "params": {}, "message": "The virtual tour has no scenes yet."})
    else:
        checks.append({"id": "tour-scenes", "code": "tour_scene_count", "status": "pass", "params": {"count": len(scenes)}, "message": f"Virtual tour contains {len(scenes)} scene(s)."})
        scene_ids = {scene.get("id") for scene in scenes if isinstance(scene, dict)}
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            if scene.get("media_id") not in valid_media_ids:
                checks.append({"id": f"scene-{scene.get('id', 'unknown')}-media", "code": "scene_media_missing", "status": "fail", "params": {"scene": scene.get("title", "Untitled")}, "message": f"Scene '{scene.get('title', 'Untitled')}' has missing or invalid media."})
            for hotspot in scene.get("hotspots", []):
                if hotspot.get("target_scene_id") not in scene_ids:
                    checks.append({"id": f"scene-{scene.get('id', 'unknown')}-hotspot", "code": "broken_hotspot", "status": "fail", "params": {"scene": scene.get("title", "Untitled")}, "message": f"Scene '{scene.get('title', 'Untitled')}' has a broken hotspot link."})
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
