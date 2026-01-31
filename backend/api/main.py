import sys
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

sys.path.append(str(Path(__file__).parent.parent))

from storage.activity_store import LocalTempStorage
from registry.series_registry import SeriesRegistry


class _DefaultRequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def _configure_logging() -> logging.Logger:
    repo_root = Path(__file__).resolve().parents[2]
    logs_dir = repo_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"backend_{timestamp}.log"

    logger = logging.getLogger("coursescope")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid duplicate handlers (e.g. reload/test runner).
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_DefaultRequestIdFilter())

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(_DefaultRequestIdFilter())

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.info("backend_start", extra={"request_id": "-"})
    logger.info("log_file=%s", str(log_path), extra={"request_id": "-"})
    return logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = _configure_logging()
    storage = LocalTempStorage()
    registry = SeriesRegistry()

    app.state.storage = storage
    app.state.registry = registry
    app.state.logger = logger

    yield


app = FastAPI(
    title="CourseScope API",
    description="Analytics pour traces GPX/FIT",
    version="1.1.22",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    logger: logging.Logger = request.app.state.logger
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "request_unhandled_exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round(duration_ms, 2),
            },
        )
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "request_id": request_id},
        )

    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": getattr(response, "status_code", None),
            "duration_ms": round(duration_ms, 2),
        },
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes.activities import router as activities_router
from api.routes.analysis import router as analysis_router
from api.routes.series import router as series_router
from api.routes.maps import router as maps_router

app.include_router(activities_router)
app.include_router(analysis_router)
app.include_router(series_router)
app.include_router(maps_router)

# Dynamic compatibility: also serve the same routes under /api/*
app.include_router(activities_router, prefix="/api", include_in_schema=False)
app.include_router(analysis_router, prefix="/api", include_in_schema=False)
app.include_router(series_router, prefix="/api", include_in_schema=False)
app.include_router(maps_router, prefix="/api", include_in_schema=False)


def get_activity_storage():
    return app.state.storage


def get_series_registry():
    return app.state.registry


@app.get("/")
async def root():
    return {
        "message": "CourseScope API",
        "version": "1.1.22",
        "docs": "/docs",
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        logger = logging.getLogger("coursescope")
        logger.info("health_check", extra={"request_id": "-"})
        storage = get_activity_storage()
        registry = get_series_registry()

        result = {
            "status": "healthy",
            "storage": "operational",
            "registry": "operational",
        }
        logger.info("health_ok", extra={"request_id": "-"})
        return result
    except Exception as e:
        logger = logging.getLogger("coursescope")
        logger.exception("health_failed", extra={"request_id": "-"})
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
