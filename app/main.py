"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.companies import router as companies_router
from app.api.health import router as health_router
from app.api.leads import router as leads_router
from app.api.pipeline import router as pipeline_router
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(health_router)
app.include_router(companies_router)
app.include_router(leads_router)
app.include_router(pipeline_router)
