from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cardops_api.config import get_settings
from cardops_api.database import init_db
from cardops_api.demo import seed_if_needed
from cardops_api.logging_config import configure_logging
from cardops_api.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    seed_if_needed()
    yield


app = FastAPI(
    title="CardOps AI API",
    version="0.1.0",
    description="Local-first sports card inventory, image ingestion, listing audit, and eBay operations API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://940smiley.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
