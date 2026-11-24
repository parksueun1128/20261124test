"""논문 피드, 분석 결과, Q&A용 Pydantic v2 스키마 정의."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GlossaryItem(BaseModel):
    """논문에 등장하는 AI 전문 용어와 쉬운 뜻풀이 항목."""

    term: str = Field(..., min_length=1, description="AI 전문 용어")
    definition: str = Field(..., min_length=1, description="입문자 눈높이의 쉬운 설명")


class PaperAnalysisLLMOutput(BaseModel):
    """LLM으로부터 Structured Output(JSON)으로 강제 수신할 스키마."""

    one_line_summary: str = Field(..., min_length=5, description="한 줄 핵심 요약")
    easy_explanation: str = Field(
        ..., min_length=20, description="비전공자도 이해할 수 있는 일상 비유 중심 설명 (3~4문단)"
    )
    key_contributions: List[str] = Field(
        ..., min_length=1, description="기존 대비 개선점 (최대 3가지)"
    )
    glossary: List[GlossaryItem] = Field(
        ..., min_length=1, description="어려운 AI 용어 사전 (최대 5개)"
    )
    difficulty_level: Literal["입문", "중급", "심화"] = Field(
        ..., description="입문자 기준 난이도"
    )

    @field_validator("key_contributions")
    @classmethod
    def limit_contributions(cls, value: List[str]) -> List[str]:
        """핵심 기여는 공백 항목을 제거하고 최대 3개로 제한합니다."""
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("key_contributions는 최소 1개 이상이어야 합니다.")
        return cleaned[:3]

    @field_validator("glossary")
    @classmethod
    def limit_glossary(cls, value: List[GlossaryItem]) -> List[GlossaryItem]:
        """용어 사전은 최대 5개로 제한합니다."""
        if not value:
            raise ValueError("glossary는 최소 1개 이상이어야 합니다.")
        return value[:5]


class PaperAnalysisResponse(BaseModel):
    """클라이언트에 반환되는 최종 논문 분석 응답 스키마."""

    model_config = ConfigDict(from_attributes=True)

    arxiv_id: str
    title: str
    one_line_summary: str
    easy_explanation: str
    key_contributions: List[str]
    glossary: List[GlossaryItem]
    difficulty_level: Literal["입문", "중급", "심화"]

    # UI 표시 및 캐시 여부 확인용 부가 메타데이터
    authors: List[str] = Field(default_factory=list)
    published_at: Optional[str] = None
    pdf_url: Optional[str] = None
    source_type: Literal["arxiv", "pdf"] = "arxiv"
    cached: bool = False
    analyzed_at: Optional[datetime] = None


class PaperSummaryItem(BaseModel):
    """최신 AI 논문 피드의 개별 논문 메타데이터."""

    arxiv_id: str
    title: str
    authors: List[str]
    published_at: str
    categories: List[str]
    summary: str
    pdf_url: str
    arxiv_url: str
    is_analyzed: bool = False


class LatestPapersResponse(BaseModel):
    """최신 AI 논문 피드 응답 스키마."""

    category: str
    total: int
    papers: List[PaperSummaryItem]


class AnalyzePaperRequest(BaseModel):
    """JSON 요청으로 arXiv 논문을 분석할 때 사용하는 입력 스키마."""

    arxiv_id: str = Field(..., min_length=3, description="arXiv ID 또는 arXiv URL")
    force_refresh: bool = Field(
        default=False, description="True일 경우 DB 캐시를 무시하고 새로 분석"
    )


class ChatMessage(BaseModel):
    """논문 Q&A 대화 이력 항목."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class PaperQARequest(BaseModel):
    """분석 완료된 논문에 대한 추가 질문 요청 스키마."""

    question: str = Field(..., min_length=1, max_length=1000, description="입문자의 질문")
    history: List[ChatMessage] = Field(
        default_factory=list, description="이전 대화 기록 (최대 최근 6개 사용)"
    )


class PaperQAResponse(BaseModel):
    """논문 Q&A 답변 응답 스키마."""

    arxiv_id: str
    answer: str
