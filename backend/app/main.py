from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "SUNNATILLO 360° STUDIO API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "application": "SUNNATILLO 360° STUDIO", "version": "0.1.0"}

@app.get("/api/capabilities")
async def capabilities():
    return {
        "local_projects": True,
        "ai_providers": [],
        "publishing_targets": [],
        "note": "External providers are opt-in and must be configured server-side."
    }