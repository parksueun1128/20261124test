"""FastAPI 애플리케이션 엔트리포인트."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import papers

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """앱 시작 시 SQLite/SQLAlchemy 테이블을 자동 초기화합니다."""
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="arXiv 최신 AI 논문 및 업로드 PDF를 입문자 눈높이로 쉽게 풀이해 주는 API",
    lifespan=lifespan,
)

# Vite 개발 서버(http://localhost:5173) 등 프론트엔드 요청 허용을 위한 CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router)


@app.get("/health", tags=["health"])
def health_check() -> Dict[str, str]:
    """서버 동작 상태 및 활성 LLM 제공자를 반환합니다."""
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
    }
