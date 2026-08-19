"""FastAPI 应用入口。"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .routers import stations

STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="中转站管理面板", version="1.0.0")

app.include_router(stations.router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))
