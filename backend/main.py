"""تطبيق FastAPI الرئيسي — منصة المصادر."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.admin import router as admin_router
from backend.api.ai import router as ai_router
from backend.api.routes import router as api_router
from backend.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="منصة المصادر — API",
        description="قاعدة معرفية موحدة للمصادر الفقهية والحديثية: بحث عربي وRAG باستناد للمصادر.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.include_router(ai_router)
    app.include_router(admin_router)

    @app.on_event("startup")
    def on_startup() -> None:
        # تهيئة فهارس البحث بصورة idempotent عند كل إقلاع
        from shared.db import fts
        from shared.db.session import create_db_engine

        engine = create_db_engine(settings.database_url)
        fts.ensure_fts(engine)

    return app


app = create_app()
