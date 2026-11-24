"""논문 피드 조회, 초보자 맞춤 분석(DB 캐싱 포함), Q&A 챗봇 API 라우터."""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.config import Settings, get_settings
from app.database import get_db
from app.models.paper import PaperAnalysis
from app.schemas.paper import (
    AnalyzePaperRequest,
    GlossaryItem,
    LatestPapersResponse,
    PaperAnalysisResponse,
    PaperQARequest,
    PaperQAResponse,
)
from app.services.arxiv_service import (
    ArxivService,
    ArxivServiceError,
    normalize_arxiv_id,
)
from app.services.llm_service import LLMService, LLMServiceError
from app.services.pdf_service import PDFService, PDFServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/papers", tags=["papers"])


# ============================================================
# FastAPI 의존성 주입 팩토리 (테스트 시 dependency_overrides로 모킹 가능)
# ============================================================
def get_arxiv_service() -> ArxivService:
    return ArxivService()


def get_pdf_service(settings: Settings = Depends(get_settings)) -> PDFService:
    return PDFService(max_chars=settings.max_paper_chars)


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return LLMService(settings=settings)


def _model_to_response(record: PaperAnalysis, cached: bool) -> PaperAnalysisResponse:
    """SQLAlchemy ORM 레코드를 API 응답 스키마로 변환합니다."""
    return PaperAnalysisResponse(
        arxiv_id=record.arxiv_id,
        title=record.title,
        one_line_summary=record.one_line_summary,
        easy_explanation=record.easy_explanation,
        key_contributions=list(record.key_contributions or []),
        glossary=[GlossaryItem.model_validate(item) for item in (record.glossary or [])],
        difficulty_level=record.difficulty_level,  # type: ignore[arg-type]
        authors=list(record.authors or []),
        published_at=record.published_at,
        pdf_url=record.pdf_url,
        source_type=record.source_type,  # type: ignore[arg-type]
        cached=cached,
        analyzed_at=record.updated_at or record.created_at,
    )


async def _parse_analyze_request(
    request: Request,
) -> Tuple[Optional[str], Optional[UploadFile], bool]:
    """JSON 요청과 multipart/form-data(PDF 업로드) 요청을 모두 수용하도록 파싱합니다."""
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            payload = await request.json()
            parsed = AnalyzePaperRequest.model_validate(payload)
            return parsed.arxiv_id, None, parsed.force_refresh
        except (ValueError, ValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"요청 JSON 형식이 올바르지 않습니다: {exc}",
            ) from exc

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        raw_arxiv_id = form.get("arxiv_id")
        raw_pdf_file = form.get("pdf_file")
        raw_force = str(form.get("force_refresh", "false")).lower()
        force_refresh = raw_force in ("true", "1", "yes", "on")

        arxiv_id = str(raw_arxiv_id).strip() if isinstance(raw_arxiv_id, str) and raw_arxiv_id.strip() else None
        pdf_file = raw_pdf_file if isinstance(raw_pdf_file, UploadFile) else None
        return arxiv_id, pdf_file, force_refresh

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="application/json 또는 multipart/form-data 형식으로 요청해 주세요.",
    )


@router.get("/latest", response_model=LatestPapersResponse)
def get_latest_papers(
    category: Optional[str] = Query(
        default=None,
        description="arXiv 카테고리 필터 (all, cs.AI, cs.LG, cs.CL)",
    ),
    query: Optional[str] = Query(
        default=None,
        max_length=120,
        description="논문 제목/초록 키워드 검색",
    ),
    max_results: int = Query(default=12, ge=1, le=30),
    db: Session = Depends(get_db),
    arxiv_service: ArxivService = Depends(get_arxiv_service),
) -> LatestPapersResponse:
    """arXiv의 최신 AI 논문 목록(cs.AI, cs.LG, cs.CL)을 조회합니다."""
    try:
        papers = arxiv_service.fetch_latest_papers(
            category=category,
            query=query,
            max_results=max_results,
        )
    except ArxivServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    # DB에 이미 분석 결과가 캐싱된 논문인지 일괄 조회하여 표시
    if papers:
        ids = [paper.arxiv_id for paper in papers]
        cached_ids = set(
            db.scalars(
                select(PaperAnalysis.arxiv_id).where(PaperAnalysis.arxiv_id.in_(ids))
            ).all()
        )
        for paper in papers:
            paper.is_analyzed = paper.arxiv_id in cached_ids

    return LatestPapersResponse(
        category=category or "all",
        total=len(papers),
        papers=papers,
    )


@router.get("/history", response_model=List[PaperAnalysisResponse])
def get_analysis_history(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[PaperAnalysisResponse]:
    """DB에 캐싱된 기존 논문 분석 이력을 최신순으로 반환합니다."""
    records = db.scalars(
        select(PaperAnalysis).order_by(desc(PaperAnalysis.updated_at)).limit(limit)
    ).all()
    return [_model_to_response(record, cached=True) for record in records]


@router.post(
    "/analyze",
    response_model=PaperAnalysisResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "arxiv_id": {
                                "type": "string",
                                "example": "2401.12345",
                            },
                            "force_refresh": {
                                "type": "boolean",
                                "default": False,
                            },
                        },
                        "required": ["arxiv_id"],
                    }
                },
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "arxiv_id": {"type": "string"},
                            "pdf_file": {"type": "string", "format": "binary"},
                            "force_refresh": {"type": "boolean", "default": False},
                        },
                    }
                },
            },
        }
    },
)
async def analyze_paper(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    arxiv_service: ArxivService = Depends(get_arxiv_service),
    pdf_service: PDFService = Depends(get_pdf_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> PaperAnalysisResponse:
    """arXiv ID 또는 업로드된 PDF 파일을 분석하여 초보자용 해설을 반환합니다.

    캐싱 분기:
    - 동일한 arXiv ID 또는 동일 해시의 PDF가 이미 DB에 저장되어 있으면
      LLM을 재호출하지 않고 즉시 캐시 결과를 반환합니다 (`cached=True`).
    - 캐시가 없거나 `force_refresh=True`인 경우에만 텍스트 추출 및 LLM 호출을 수행합니다.
    """
    raw_arxiv_id, pdf_file, force_refresh = await _parse_analyze_request(request)

    if not raw_arxiv_id and pdf_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="분석할 arXiv ID(또는 URL)를 입력하거나 PDF 파일을 업로드해 주세요.",
        )

    # ------------------------------------------------------------
    # 분기 A: PDF 직접 업로드 분석
    # ------------------------------------------------------------
    if pdf_file is not None:
        filename = pdf_file.filename or "uploaded_paper.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF 파일(.pdf)만 업로드할 수 있습니다.",
            )

        pdf_bytes = await pdf_file.read()
        max_bytes = settings.max_pdf_size_mb * 1024 * 1024
        if not pdf_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업로드된 PDF 파일이 비어 있습니다.",
            )
        if len(pdf_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"PDF 파일 크기는 최대 {settings.max_pdf_size_mb}MB까지 지원합니다.",
            )
        if not pdf_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효한 PDF 바이너리 형식이 아닙니다.",
            )

        cache_key = pdf_service.compute_pdf_cache_key(pdf_bytes)

        # DB 캐시 조회 (동일 PDF 재업로드 시 즉시 반환)
        existing = db.scalar(
            select(PaperAnalysis).where(PaperAnalysis.arxiv_id == cache_key)
        )
        if existing and not force_refresh:
            return _model_to_response(existing, cached=True)

        try:
            full_text, inferred_title = pdf_service.extract_text_from_pdf(pdf_bytes)
            paper_excerpt = pdf_service.extract_key_sections(
                full_text, max_chars=settings.max_paper_chars
            )
        except PDFServiceError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        title = inferred_title or Path(filename).stem
        authors: List[str] = []
        published_at: Optional[str] = None
        pdf_url: Optional[str] = None
        source_type = "pdf"

    # ------------------------------------------------------------
    # 분기 B: arXiv ID / URL 기반 분석
    # ------------------------------------------------------------
    else:
        assert raw_arxiv_id is not None
        try:
            cache_key = normalize_arxiv_id(raw_arxiv_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        # DB 캐시 조회 (이미 분석된 arXiv 논문이면 즉시 반환)
        existing = db.scalar(
            select(PaperAnalysis).where(PaperAnalysis.arxiv_id == cache_key)
        )
        if existing and not force_refresh:
            return _model_to_response(existing, cached=True)

        try:
            meta = arxiv_service.fetch_paper_by_id(cache_key)
        except ArxivServiceError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        title = meta.title
        authors = meta.authors
        published_at = meta.published_at
        pdf_url = meta.pdf_url
        source_type = "arxiv"

        # 원문 PDF 다운로드 및 핵심 섹션 추출 시도 (실패 시 초록으로 안전 폴백)
        try:
            pdf_bytes = pdf_service.download_pdf(meta.pdf_url)
            full_text, _ = pdf_service.extract_text_from_pdf(pdf_bytes)
            combined_text = f"Abstract:\n{meta.summary}\n\n{full_text}"
            paper_excerpt = pdf_service.extract_key_sections(
                combined_text, max_chars=settings.max_paper_chars
            )
        except PDFServiceError as exc:
            logger.warning(
                "PDF 추출 실패로 초록 기반 분석으로 폴백합니다 (arxiv_id=%s): %s",
                cache_key,
                exc,
            )
            paper_excerpt = f"Title: {meta.title}\n\nAbstract:\n{meta.summary}"

    # ------------------------------------------------------------
    # LLM 분석 호출 및 DB 캐시 저장(Upsert)
    # ------------------------------------------------------------
    try:
        analysis = llm_service.analyze_paper(title=title, paper_text=paper_excerpt)
    except LLMServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    glossary_dicts = [item.model_dump() for item in analysis.glossary]

    if existing:
        existing.title = title
        existing.authors = authors
        existing.published_at = published_at
        existing.pdf_url = pdf_url
        existing.source_type = source_type
        existing.one_line_summary = analysis.one_line_summary
        existing.easy_explanation = analysis.easy_explanation
        existing.key_contributions = analysis.key_contributions
        existing.glossary = glossary_dicts
        existing.difficulty_level = analysis.difficulty_level
        existing.source_text_excerpt = paper_excerpt
        existing.llm_provider = llm_service.provider_name
        existing.llm_model = llm_service.model_name
        record = existing
    else:
        record = PaperAnalysis(
            arxiv_id=cache_key,
            title=title,
            authors=authors,
            published_at=published_at,
            pdf_url=pdf_url,
            source_type=source_type,
            one_line_summary=analysis.one_line_summary,
            easy_explanation=analysis.easy_explanation,
            key_contributions=analysis.key_contributions,
            glossary=glossary_dicts,
            difficulty_level=analysis.difficulty_level,
            source_text_excerpt=paper_excerpt,
            llm_provider=llm_service.provider_name,
            llm_model=llm_service.model_name,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return _model_to_response(record, cached=False)


@router.post("/{arxiv_id:path}/qa", response_model=PaperQAResponse)
def ask_paper_question(
    arxiv_id: str,
    payload: PaperQARequest,
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> PaperQAResponse:
    """분석 완료된 논문에 대해 초보자가 추가 질문할 수 있는 Q&A 챗봇 엔드포인트."""
    lookup_key = arxiv_id.strip()
    if not lookup_key.startswith("pdf:"):
        try:
            lookup_key = normalize_arxiv_id(lookup_key)
        except ValueError:
            pass

    record = db.scalar(
        select(PaperAnalysis).where(PaperAnalysis.arxiv_id == lookup_key)
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="먼저 해당 논문의 분석을 완료한 뒤 질문할 수 있습니다.",
        )

    contributions_text = "\n".join(
        f"- {item}" for item in (record.key_contributions or [])
    )
    summary_context = (
        f"한 줄 요약: {record.one_line_summary}\n\n"
        f"쉬운 설명:\n{record.easy_explanation}\n\n"
        f"핵심 기여:\n{contributions_text}"
    )

    try:
        answer = llm_service.answer_question(
            title=record.title,
            summary_context=summary_context,
            paper_excerpt=record.source_text_excerpt or "",
            question=payload.question,
            history=payload.history,
        )
    except LLMServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return PaperQAResponse(arxiv_id=record.arxiv_id, answer=answer)
