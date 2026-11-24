"""arxiv_service 단위 테스트 (외부 네트워크 없이 Mock 클라이언트 사용)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.arxiv_service import (
    ArxivService,
    ArxivServiceError,
    normalize_arxiv_id,
)


def _make_fake_arxiv_result(
    short_id: str = "2401.12345v2",
    title: str = "Attention\n  Is Still   All You Need",
    summary: str = "We propose a   lightweight transformer architecture.\nIt improves speed.",
) -> SimpleNamespace:
    """arxiv.Result 객체를 대체하는 테스트용 더미 객체를 생성합니다."""
    return SimpleNamespace(
        get_short_id=lambda: short_id,
        title=title,
        authors=[SimpleNamespace(name="Alice Kim"), SimpleNamespace(name="Bob Lee")],
        published=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
        categories=["cs.AI", "cs.LG"],
        summary=summary,
        pdf_url=f"https://arxiv.org/pdf/{short_id}.pdf",
        entry_id=f"https://arxiv.org/abs/{short_id}",
    )


def test_normalize_arxiv_id_variants() -> None:
    """다양한 형식의 arXiv URL/ID 입력이 정규화된 ID로 변환되는지 검증합니다."""
    assert normalize_arxiv_id("2401.12345") == "2401.12345"
    assert normalize_arxiv_id("2401.12345v3") == "2401.12345"
    assert normalize_arxiv_id("https://arxiv.org/abs/2401.12345v1") == "2401.12345"
    assert normalize_arxiv_id("https://arxiv.org/pdf/2401.12345.pdf") == "2401.12345"

    with pytest.raises(ValueError):
        normalize_arxiv_id("not-a-valid-arxiv-id")


def test_fetch_latest_papers_parses_and_cleans_results() -> None:
    """최신 논문 조회 시 카테고리 쿼리 생성과 텍스트 정제가 올바르게 동작하는지 검증합니다."""
    mock_client = MagicMock()
    mock_client.results.return_value = [_make_fake_arxiv_result()]

    service = ArxivService(client=mock_client)
    papers = service.fetch_latest_papers(category="cs.AI", query="transformer", max_results=5)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.arxiv_id == "2401.12345"
    assert paper.title == "Attention Is Still All You Need"
    assert paper.authors == ["Alice Kim", "Bob Lee"]
    assert paper.published_at == "2026-03-15"
    assert "lightweight transformer" in paper.summary

    # arXiv Search 객체에 카테고리와 키워드가 모두 반영되었는지 확인
    called_search = mock_client.results.call_args[0][0]
    assert "cat:cs.AI" in called_search.query
    assert 'all:"transformer"' in called_search.query


def test_fetch_latest_papers_rejects_unsupported_category() -> None:
    """지원하지 않는 카테고리 요청 시 ArxivServiceError가 발생하는지 확인합니다."""
    service = ArxivService(client=MagicMock())

    with pytest.raises(ArxivServiceError):
        service.fetch_latest_papers(category="physics.gen-ph")


def test_fetch_paper_by_id_raises_when_missing() -> None:
    """존재하지 않는 arXiv ID 조회 시 ArxivServiceError를 발생시키는지 확인합니다."""
    mock_client = MagicMock()
    mock_client.results.return_value = []
    service = ArxivService(client=mock_client)

    with pytest.raises(ArxivServiceError):
        service.fetch_paper_by_id("2401.99999")
