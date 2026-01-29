import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(str(Path(__file__).parent.parent))

from storage.activity_store import LocalTempStorage
from registry.series_registry import SeriesRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = LocalTempStorage()
    registry = SeriesRegistry()

    app.state.storage = storage
    app.state.registry = registry

    yield


app = FastAPI(
    title="CourseScope API",
    description="Analytics pour traces GPX/FIT",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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


def get_activity_storage():
    return app.state.storage


def get_series_registry():
    return app.state.registry


@app.get("/")
async def root():
    return {
        "message": "CourseScope API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        storage = get_activity_storage()
        registry = get_series_registry()

        return {
            "status": "healthy",
            "storage": "operational",
            "registry": "operational",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
