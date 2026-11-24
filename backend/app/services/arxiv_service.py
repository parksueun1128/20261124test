"""arXiv API 연동 및 최신 AI 논문 검색 서비스."""

import re
from typing import List, Optional

import arxiv

from app.schemas.paper import PaperSummaryItem

# 지원하는 AI 핵심 카테고리
SUPPORTED_CATEGORIES = ("cs.AI", "cs.LG", "cs.CL")

# arXiv URL 또는 버전 포함 ID에서 정규화된 ID를 추출하기 위한 패턴
_ARXIV_NEW_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?")
_ARXIV_OLD_ID_RE = re.compile(r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?")


class ArxivServiceError(Exception):
    """arXiv 조회 실패 시 발생하는 예외."""


def normalize_arxiv_id(raw_input: str) -> str:
    """arXiv URL, PDF 경로, 버전 번호가 포함된 입력을 정규화된 arXiv ID로 변환합니다.

    예시:
    - "https://arxiv.org/abs/2401.12345v2" -> "2401.12345"
    - "https://arxiv.org/pdf/2401.12345.pdf" -> "2401.12345"
    - "2401.12345v1" -> "2401.12345"
    """
    cleaned = raw_input.strip()
    if not cleaned:
        raise ValueError("arXiv ID 또는 URL이 비어 있습니다.")

    # 앞뒤 경로 및 .pdf 확장자 제거
    cleaned = cleaned.replace(".pdf", "")

    new_match = _ARXIV_NEW_ID_RE.search(cleaned)
    if new_match:
        return new_match.group(1)

    old_match = _ARXIV_OLD_ID_RE.search(cleaned)
    if old_match:
        return old_match.group(1)

    raise ValueError(
        f"올바른 arXiv ID 또는 URL 형식이 아닙니다: '{raw_input}' (예: 2401.12345 또는 https://arxiv.org/abs/2401.12345)"
    )


def _clean_whitespace(text: str) -> str:
    """줄바꿈과 연속 공백을 단일 공백으로 정리합니다."""
    return re.sub(r"\s+", " ", text or "").strip()


class ArxivService:
    """arXiv API에서 최신 AI 논문 목록과 개별 논문 메타데이터를 조회하는 서비스."""

    def __init__(self, client: Optional[arxiv.Client] = None) -> None:
        self._client = client or arxiv.Client(
            page_size=20,
            delay_seconds=1.0,
            num_retries=2,
        )

    def _to_paper_summary(self, result: arxiv.Result) -> PaperSummaryItem:
        """arxiv.Result 객체를 Pydantic 응답 모델로 변환합니다."""
        raw_id = result.get_short_id()
        normalized_id = normalize_arxiv_id(raw_id)
        published_str = (
            result.published.strftime("%Y-%m-%d") if result.published else ""
        )
        pdf_url = result.pdf_url or f"https://arxiv.org/pdf/{normalized_id}.pdf"
        arxiv_url = result.entry_id or f"https://arxiv.org/abs/{normalized_id}"

        return PaperSummaryItem(
            arxiv_id=normalized_id,
            title=_clean_whitespace(result.title),
            authors=[author.name for author in result.authors],
            published_at=published_str,
            categories=list(result.categories or []),
            summary=_clean_whitespace(result.summary),
            pdf_url=pdf_url,
            arxiv_url=arxiv_url,
        )

    def fetch_latest_papers(
        self,
        category: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 12,
    ) -> List[PaperSummaryItem]:
        """cs.AI, cs.LG, cs.CL 카테고리의 최신 논문 목록을 가져옵니다."""
        if category and category.lower() != "all":
            if category not in SUPPORTED_CATEGORIES:
                raise ArxivServiceError(
                    f"지원하지 않는 카테고리입니다: {category}. "
                    f"({', '.join(SUPPORTED_CATEGORIES)} 중 선택)"
                )
            cat_query = f"cat:{category}"
        else:
            cat_query = " OR ".join(f"cat:{cat}" for cat in SUPPORTED_CATEGORIES)

        # 키워드 검색이 함께 전달된 경우 카테고리 조건과 AND로 결합
        if query and query.strip():
            safe_keyword = query.strip().replace('"', "")
            search_query = f"({cat_query}) AND all:\"{safe_keyword}\""
        else:
            search_query = cat_query

        search = arxiv.Search(
            query=search_query,
            max_results=max(1, min(max_results, 30)),
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        try:
            results = list(self._client.results(search))
        except Exception as exc:
            raise ArxivServiceError(
                f"arXiv API에서 최신 논문을 불러오는 중 오류가 발생했습니다: {exc}"
            ) from exc

        return [self._to_paper_summary(item) for item in results]

    def fetch_paper_by_id(self, raw_arxiv_id: str) -> PaperSummaryItem:
        """특정 arXiv ID의 논문 메타데이터를 조회합니다."""
        normalized_id = normalize_arxiv_id(raw_arxiv_id)
        search = arxiv.Search(id_list=[normalized_id])

        try:
            results = list(self._client.results(search))
        except Exception as exc:
            raise ArxivServiceError(
                f"arXiv 논문({normalized_id}) 조회 중 오류가 발생했습니다: {exc}"
            ) from exc

        if not results:
            raise ArxivServiceError(
                f"arXiv에서 논문 ID '{normalized_id}'를 찾을 수 없습니다."
            )

        return self._to_paper_summary(results[0])
