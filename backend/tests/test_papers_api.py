"""FastAPI 논문 분석 엔드포인트 및 DB 캐싱 동작 통합 테스트."""

from typing import Generator
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.routers.papers import get_arxiv_service, get_llm_service, get_pdf_service
from app.schemas.paper import GlossaryItem, PaperAnalysisLLMOutput, PaperSummaryItem
from app.services.llm_service import LLMService
from app.services.pdf_service import PDFService
from tests.test_llm_service import DummyLLMProvider


@pytest.fixture()
def test_db_session() -> Generator[Session, None, None]:
    """테스트마다 격리된 인메모리 SQLite DB 세션을 생성합니다."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_analyze_paper_uses_db_cache_on_second_request(test_db_session: Session) -> None:
    """동일한 arXiv ID를 두 번 분석 요청할 때 두 번째 요청은 DB 캐시를 반환하는지 검증합니다."""
    sample_output = PaperAnalysisLLMOutput(
        one_line_summary="작은 모델로도 대형 모델 수준의 추론 성능을 달성하는 증류 기법입니다.",
        easy_explanation=(
            "베테랑 요리사의 레시피 핵심만 압축해 초보 요리사에게 전수하는 과정과 비슷합니다.\n\n"
            "큰 모델의 생각 과정을 단계별로 따라 배우게 만들어 훨씬 적은 메모리로도 좋은 답을 냅니다."
        ),
        key_contributions=["추론 비용 60% 절감", "모바일 환경 구동 가능"],
        glossary=[GlossaryItem(term="Knowledge Distillation", definition="큰 AI 모델의 지식을 작은 모델에 옮겨 심는 학습 기법")],
        difficulty_level="입문",
    )
    dummy_provider = DummyLLMProvider(sample_output)
    mock_llm_service = LLMService(provider=dummy_provider)

    mock_arxiv_service = MagicMock()
    mock_arxiv_service.fetch_paper_by_id.return_value = PaperSummaryItem(
        arxiv_id="2501.00001",
        title="Distilling Reasoning into Small Models",
        authors=["Jane Doe"],
        published_at="2025-01-10",
        categories=["cs.AI"],
        summary="We study knowledge distillation for efficient reasoning.",
        pdf_url="https://arxiv.org/pdf/2501.00001.pdf",
        arxiv_url="https://arxiv.org/abs/2501.00001",
    )

    mock_pdf_service = MagicMock(spec=PDFService)
    mock_pdf_service.download_pdf.return_value = b"%PDF-1.4 dummy"
    mock_pdf_service.extract_text_from_pdf.return_value = ("Abstract\nSample body", None)
    mock_pdf_service.extract_key_sections.return_value = "Abstract\nSample body"

    def override_get_db() -> Generator[Session, None, None]:
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_arxiv_service] = lambda: mock_arxiv_service
    app.dependency_overrides[get_pdf_service] = lambda: mock_pdf_service
    app.dependency_overrides[get_llm_service] = lambda: mock_llm_service

    try:
        client = TestClient(app)

        # 1차 요청: 캐시 미스 -> LLM 호출 발생 (cached=False)
        res1 = client.post("/api/papers/analyze", json={"arxiv_id": "2501.00001"})
        assert res1.status_code == 200
        body1 = res1.json()
        assert body1["arxiv_id"] == "2501.00001"
        assert body1["cached"] is False
        assert dummy_provider.call_count == 1

        # 2차 요청: 캐시 히트 -> LLM 재호출 없이 즉시 반환 (cached=True)
        res2 = client.post("/api/papers/analyze", json={"arxiv_id": "https://arxiv.org/abs/2501.00001v1"})
        assert res2.status_code == 200
        body2 = res2.json()
        assert body2["cached"] is True
        assert body2["one_line_summary"] == body1["one_line_summary"]
        assert dummy_provider.call_count == 1

        # 3차 요청: 분석 완료된 논문에 대한 Q&A 챗봇 테스트
        res_qa = client.post(
            "/api/papers/2501.00001/qa",
            json={"question": "이 기술은 어디에 쓰이나요?", "history": []},
        )
        assert res_qa.status_code == 200
        assert "쉬운 답변" in res_qa.json()["answer"]
    finally:
        app.dependency_overrides.clear()
