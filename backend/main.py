from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import init_db
from backend.routers import auth, categories, channels, collect, posts

@asynccontextmanager
async def lifespan(app: FastAPI):
    import config
    config.validate_telegram_config()
    await init_db()
    from backend.routers.collect import start_scheduler_if_enabled
    start_scheduler_if_enabled()
    yield
    # shutdown if needed


app = FastAPI(title="TGSOS", description="Telegram channels aggregator", lifespan=lifespan)

app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
app.include_router(collect.router, prefix="/api/collect", tags=["collect"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

import os

frontend_dist = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(frontend_dist):
    app.mount("/static", StaticFiles(directory=frontend_dist), name="static")


@app.get("/")
async def index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "TGSOS API", "docs": "/docs"}
