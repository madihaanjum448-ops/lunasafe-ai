"""LunaSafe AI backend entry point.   Run:  uvicorn app.main:app --reload --port 8000"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routes.api import router
from app.services.metadata import ImageValidationError

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Lunar landing HAZARD SCREENING prototype using orbital imagery. "
        "Not a flight-certified safety system; results do not guarantee a safe landing."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ImageValidationError)
async def image_validation_handler(_: Request, exc: ImageValidationError):
    # Same shape as FastAPI's own errors so the frontend handles one format.
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(router)


@app.get("/", include_in_schema=False)
def root():
    return {"message": "LunaSafe AI backend. API docs at /docs", "health": "/api/health"}
