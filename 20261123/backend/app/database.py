"""SQLAlchemy 데이터베이스 엔진 및 세션 관리 모듈."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# SQLite 사용 시 멀티스레드 요청을 허용하기 위한 connect_args 분기
# 추후 PostgreSQL로 전환하면 자동으로 connect_args가 비워집니다.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """모든 ORM 모델이 상속받는 선언적 베이스 클래스."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends용 데이터베이스 세션 제너레이터."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """등록된 모든 ORM 테이블을 생성합니다."""
    # 모델을 import하여 Base.metadata에 테이블 정의가 등록되도록 보장
    from app.models import paper  # noqa: F401

    Base.metadata.create_all(bind=engine)
