"""llm_service 및 pdf_service 핵심 섹션 추출 단위 테스트 (LLM API 모킹)."""

from typing import List
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.paper import ChatMessage, GlossaryItem, PaperAnalysisLLMOutput
from app.services.llm_service import (
    BaseLLMProvider,
    LLMService,
    LLMServiceError,
    OpenAIProvider,
    _extract_json_object,
)
from app.services.pdf_service import PDFService


class DummyLLMProvider(BaseLLMProvider):
    """외부 API 호출 없이 LLMService 동작을 검증하기 위한 테스트용 Provider."""

    provider_name = "mock"
    model_name = "mock-model-v1"

    def __init__(self, output: PaperAnalysisLLMOutput) -> None:
        self._output = output
        self.call_count = 0

    def generate_structured_analysis(
        self, title: str, paper_text: str
    ) -> PaperAnalysisLLMOutput:
        self.call_count += 1
        return self._output

    def answer_question(
        self,
        title: str,
        summary_context: str,
        paper_excerpt: str,
        question: str,
        history: List[ChatMessage],
    ) -> str:
        return f"'{title}' 논문에 대한 쉬운 답변: {question}"


def _sample_llm_output() -> PaperAnalysisLLMOutput:
    return PaperAnalysisLLMOutput(
        one_line_summary="문장의 핵심 단어에만 집중해 더 빠르고 정확하게 번역하는 모델입니다.",
        easy_explanation=(
            "긴 책을 처음부터 끝까지 외우는 대신 중요한 문장에 형광펜을 치며 읽는 것과 같습니다.\n\n"
            "기존 방식은 앞에서부터 한 단어씩 순서대로 처리해 문장이 길어지면 앞 내용을 까먹기 쉬웠습니다.\n\n"
            "이 논문은 모든 단어를 동시에 살펴보며 서로 연관된 단어끼리 바로 연결하는 방식을 제안합니다."
        ),
        key_contributions=[
            "순환 신경망 없이 병렬 처리로 학습 속도를 크게 향상",
            "긴 문장에서도 문맥 손실 없이 번역 품질 개선",
        ],
        glossary=[
            GlossaryItem(term="Self-Attention", definition="문장 속 각 단어가 다른 단어들과 얼마나 관련 있는지 점수를 매기는 계산 방식"),
            GlossaryItem(term="Transformer", definition="어텐션 메커니즘을 중심으로 설계된 현대 AI의 핵심 신경망 구조"),
        ],
        difficulty_level="입문",
    )


def test_llm_service_analyze_paper_with_mock_provider() -> None:
    """LLMService가 주입된 Provider를 통해 검증된 Pydantic 결과를 반환하는지 확인합니다."""
    provider = DummyLLMProvider(_sample_llm_output())
    service = LLMService(provider=provider)

    result = service.analyze_paper(
        title="Attention Is All You Need",
        paper_text="Abstract: The dominant sequence transduction models...",
    )

    assert provider.call_count == 1
    assert result.difficulty_level == "입문"
    assert len(result.key_contributions) == 2
    assert result.glossary[0].term == "Self-Attention"


def test_llm_service_rejects_empty_text() -> None:
    """빈 텍스트 입력 시 LLM 호출 전 예외가 발생하는지 확인합니다."""
    provider = DummyLLMProvider(_sample_llm_output())
    service = LLMService(provider=provider)

    with pytest.raises(LLMServiceError):
        service.analyze_paper(title="Empty", paper_text="   ")

    assert provider.call_count == 0


def test_openai_provider_structured_output_mock() -> None:
    """OpenAIProvider가 Structured Output 응답을 정상 파싱하는지 모킹 검증합니다."""
    expected = _sample_llm_output()
    fake_message = MagicMock()
    fake_message.parsed = expected
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=fake_message)]

    with patch("app.services.llm_service.OpenAI") as mock_openai_cls:
        mock_instance = mock_openai_cls.return_value
        mock_instance.beta.chat.completions.parse.return_value = fake_completion

        provider = OpenAIProvider(api_key="sk-test-valid-key", model="gpt-4o-mini")
        result = provider.generate_structured_analysis(
            title="Test Paper",
            paper_text="Some paper content for testing.",
        )

    assert result.one_line_summary == expected.one_line_summary
    assert result.difficulty_level == "입문"


def test_extract_json_object_strips_markdown_fence() -> None:
    """LLM이 마크다운 코드블록을 섞어 보내도 순수 JSON 객체만 추출하는지 확인합니다."""
    raw = '여기 분석 결과입니다:\n```json\n{"one_line_summary": "요약"}\n```'
    assert _extract_json_object(raw) == '{"one_line_summary": "요약"}'


def test_schema_clamps_contributions_and_validates_difficulty() -> None:
    """핵심 기여 최대 3개 제한 및 difficulty_level 리터럴 검증을 확인합니다."""
    output = PaperAnalysisLLMOutput(
        one_line_summary="충분히 긴 한 줄 요약 문장입니다.",
        easy_explanation="이것은 입문자도 쉽게 이해할 수 있도록 작성된 충분한 길이의 비유 설명입니다.",
        key_contributions=["기여 1", "기여 2", "기여 3", "기여 4"],
        glossary=[GlossaryItem(term="LLM", definition="초거대 언어 모델")],
        difficulty_level="중급",
    )
    assert len(output.key_contributions) == 3

    with pytest.raises(ValidationError):
        PaperAnalysisLLMOutput(
            one_line_summary="충분히 긴 한 줄 요약 문장입니다.",
            easy_explanation="이것은 입문자도 쉽게 이해할 수 있도록 작성된 충분한 길이의 비유 설명입니다.",
            key_contributions=["기여 1"],
            glossary=[GlossaryItem(term="LLM", definition="초거대 언어 모델")],
            difficulty_level="전문가",  # type: ignore[arg-type]
        )


def test_pdf_service_truncates_and_prioritizes_key_sections() -> None:
    """긴 논문 텍스트가 max_chars 이내로 축약되며 핵심 섹션이 보존되는지 확인합니다."""
    pdf_service = PDFService(max_chars=1200)
    long_body = "Detailed math derivation. " * 200
    full_text = (
        "Abstract\nThis paper solves an important AI problem.\n\n"
        "1. Introduction\nDeep learning models need lots of data.\n\n"
        f"2. Method\n{long_body}\n\n"
        "5. Conclusion\nOur approach achieves state-of-the-art results with 50% less compute."
    )

    excerpt = pdf_service.extract_key_sections(full_text)
    assert len(excerpt) <= 1300  # 생략 안내 문구 포함 허용 오차
    assert "Abstract" in excerpt
    assert "Introduction" in excerpt
    assert "Conclusion" in excerpt
