"""논문 분석 캐싱용 SQLAlchemy ORM 모델."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    """타임존 정보가 포함된 현재 UTC 시각을 반환합니다."""
    return datetime.now(timezone.utc)


class PaperAnalysis(Base):
    """LLM 분석 결과를 캐싱하는 테이블 (SQLite/PostgreSQL 호환 설계)."""

    __tablename__ = "paper_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # arXiv 논문은 정규화된 ID(예: 2401.12345), PDF 업로드는 "pdf:<sha256앞16자리>"를 키로 사용
    arxiv_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    authors: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    published_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_type: Mapped[str] = mapped_column(String(16), default="arxiv", nullable=False)

    # LLM 분석 핵심 결과 필드
    one_line_summary: Mapped[str] = mapped_column(Text, nullable=False)
    easy_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    key_contributions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    glossary: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(16), nullable=False)

    # 후속 Q&A 챗봇에서 재활용할 원문 발췌 텍스트
    source_text_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 사용된 LLM 메타데이터
    llm_provider: Mapped[str] = mapped_column(String(32), default="openai", nullable=False)
    llm_model: Mapped[str] = mapped_column(String(128), default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
