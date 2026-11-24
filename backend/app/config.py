"""환경변수 기반 애플리케이션 설정 모듈."""

from functools import lru_cache
from typing import List, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """`.env` 파일 및 OS 환경변수를 읽어오는 전역 설정 클래스."""

    app_name: str = "EasyPaper AI API"
    app_version: str = "1.0.0"

    # LLM 제공자 추상화 설정 (openai | anthropic)
    llm_provider: Literal["openai", "anthropic"] = "openai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # SQLite 기본값 (추후 PostgreSQL URL로 교체 가능)
    database_url: str = "sqlite:///./easypaper.db"

    # Vite 개발 서버 요청을 허용하기 위한 CORS 설정
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM 입력 토큰 초과 방지를 위한 최대 추출 문자 수
    max_paper_chars: int = 18000

    # 업로드 PDF 최대 크기 (20MB)
    max_pdf_size_mb: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        """쉼표로 구분된 CORS 오리진 문자열을 리스트로 변환합니다."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """설정 객체를 싱글톤 형태로 캐싱하여 반환합니다."""
    return Settings()
