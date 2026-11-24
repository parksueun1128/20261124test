"""LLM 추상화 레이어(OpenAI / Anthropic Claude) 및 Structured Output 검증 서비스."""

from abc import ABC, abstractmethod
import json
import re
from typing import List, Optional

from anthropic import Anthropic
from openai import OpenAI
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas.paper import ChatMessage, PaperAnalysisLLMOutput


class LLMServiceError(Exception):
    """LLM 호출 또는 응답 스키마 검증 실패 시 발생하는 예외."""


# 입문자 맞춤 논문 분석용 시스템 프롬프트
ANALYSIS_SYSTEM_PROMPT = """당신은 복잡한 AI 연구 논문을 비전공자와 대학 입문자도 한눈에 이해할 수 있도록 설명하는 친절한 AI 튜터입니다.
반드시 한국어로 작성하며, 다음 규칙을 엄격히 지키세요:
1. one_line_summary: 논문의 핵심 아이디어를 1문장(50~90자 내외)으로 명쾌하게 요약합니다.
2. easy_explanation: 일상생활의 친숙한 비유(요리, 도서관, 지도, 팀 프로젝트 등)를 활용해 3~4문단으로 쉽게 설명합니다. 문단 사이는 줄바꿈(\n\n)으로 구분하세요.
3. key_contributions: 이 논문이 기존 방법 대비 무엇을 개선했는지 핵심만 최대 3가지 리스트로 정리합니다.
4. glossary: 논문에 등장하는 어려운 AI/머신러닝 전문 용어를 최대 5개 선정해 초보자 눈높이로 풀이합니다.
5. difficulty_level: AI 입문자 기준 난이도를 '입문', '중급', '심화' 중 하나로 정확히 분류합니다.
6. 반드시 요청된 JSON 스키마 형식만 출력하며, 불필요한 마크다운 설명이나 서론을 덧붙이지 마세요."""

QA_SYSTEM_PROMPT = """당신은 AI 논문을 처음 읽는 학생의 질문에 친절하게 답해주는 AI 튜터입니다.
제공된 논문 요약 및 본문 발췌 내용을 바탕으로 사실에 근거해 한국어로 답변하세요.
어려운 수식이나 전문 용어가 나오면 반드시 일상적인 비유를 함께 들어 2~4문단 이내로 명확하게 설명해 주세요.
논문에 명시되지 않은 내용은 추측하지 말고, 논문에서 다루지 않는 내용임을 솔직히 안내하세요."""


def _build_analysis_user_prompt(title: str, paper_text: str) -> str:
    """논문 제목과 발췌 본문을 결합해 LLM 입력 프롬프트를 생성합니다."""
    return (
        f"다음 AI 논문을 분석하여 입문자용 해설 JSON을 작성해 주세요.\n\n"
        f"[논문 제목]\n{title}\n\n"
        f"[논문 핵심 발췌 내용]\n{paper_text}"
    )


def _extract_json_object(raw_text: str) -> str:
    """혹시 마크다운 코드블록(```json ... ```)이 섞여 들어오더라도 순수 JSON 문자열만 안전하게 추출합니다."""
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


class BaseLLMProvider(ABC):
    """OpenAI / Anthropic 등 다양한 LLM 제공자를 교체하기 위한 추상 인터페이스."""

    provider_name: str
    model_name: str

    @abstractmethod
    def generate_structured_analysis(
        self, title: str, paper_text: str
    ) -> PaperAnalysisLLMOutput:
        """논문 텍스트를 분석하여 Pydantic 검증이 완료된 구조화 결과를 반환합니다."""

    @abstractmethod
    def answer_question(
        self,
        title: str,
        summary_context: str,
        paper_excerpt: str,
        question: str,
        history: List[ChatMessage],
    ) -> str:
        """분석된 논문 컨텍스트를 바탕으로 사용자의 추가 질문에 답변합니다."""


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API 기반 Structured Outputs 구현체."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        if not api_key or api_key.startswith("sk-your-"):
            raise LLMServiceError(
                "OPENAI_API_KEY가 설정되지 않았습니다. backend/.env 파일에 유효한 API 키를 입력해 주세요."
            )
        self.provider_name = "openai"
        self.model_name = model
        self._client = OpenAI(api_key=api_key)

    def generate_structured_analysis(
        self, title: str, paper_text: str
    ) -> PaperAnalysisLLMOutput:
        user_prompt = _build_analysis_user_prompt(title, paper_text)
        try:
            # OpenAI Structured Outputs(Pydantic 스키마 강제) 우선 사용
            completion = self._client.beta.chat.completions.parse(
                model=self.model_name,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=PaperAnalysisLLMOutput,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is not None:
                return parsed

            # 파싱 객체가 비어 있으면 원문 JSON 폴백 파싱 수행
            raw_content = completion.choices[0].message.content or ""
            return PaperAnalysisLLMOutput.model_validate_json(
                _extract_json_object(raw_content)
            )
        except ValidationError as exc:
            raise LLMServiceError(
                f"LLM 응답이 지정된 JSON 스키마 검증에 실패했습니다: {exc}"
            ) from exc
        except Exception as exc:
            raise LLMServiceError(f"OpenAI 논문 분석 호출 실패: {exc}") from exc

    def answer_question(
        self,
        title: str,
        summary_context: str,
        paper_excerpt: str,
        question: str,
        history: List[ChatMessage],
    ) -> str:
        messages = [
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    f"[대상 논문 제목]\n{title}\n\n"
                    f"[사전 분석 요약]\n{summary_context}\n\n"
                    f"[논문 원문 발췌]\n{paper_excerpt[:8000]}"
                ),
            },
        ]
        for msg in history[-6:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": question})

        try:
            completion = self._client.chat.completions.create(
                model=self.model_name,
                temperature=0.4,
                messages=messages,
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as exc:
            raise LLMServiceError(f"OpenAI Q&A 호출 실패: {exc}") from exc


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API 기반 Tool-Use 강제 JSON 스키마 구현체."""

    def __init__(
        self, api_key: str, model: str = "claude-3-5-sonnet-20241022"
    ) -> None:
        if not api_key or api_key.startswith("sk-ant-your-"):
            raise LLMServiceError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. backend/.env 파일에 유효한 API 키를 입력해 주세요."
            )
        self.provider_name = "anthropic"
        self.model_name = model
        self._client = Anthropic(api_key=api_key)

    def generate_structured_analysis(
        self, title: str, paper_text: str
    ) -> PaperAnalysisLLMOutput:
        user_prompt = _build_analysis_user_prompt(title, paper_text)
        schema = PaperAnalysisLLMOutput.model_json_schema()

        try:
            # Claude에서 JSON 파싱 오류를 막기 위해 tool_choice로 스키마 출력 강제
            response = self._client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                temperature=0.3,
                system=ANALYSIS_SYSTEM_PROMPT,
                tools=[
                    {
                        "name": "submit_paper_analysis",
                        "description": "입문자용 논문 분석 결과를 정해진 JSON 스키마로 제출합니다.",
                        "input_schema": schema,
                    }
                ],
                tool_choice={"type": "tool", "name": "submit_paper_analysis"},
                messages=[{"role": "user", "content": user_prompt}],
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_paper_analysis":
                    return PaperAnalysisLLMOutput.model_validate(block.input)

            # 예외적으로 text 블록만 온 경우 안전 JSON 추출 후 검증
            text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
            raw_json = _extract_json_object("\n".join(text_blocks))
            return PaperAnalysisLLMOutput.model_validate(json.loads(raw_json))
        except (ValidationError, json.JSONDecodeError) as exc:
            raise LLMServiceError(
                f"Claude 응답이 지정된 JSON 스키마 검증에 실패했습니다: {exc}"
            ) from exc
        except Exception as exc:
            raise LLMServiceError(f"Anthropic 논문 분석 호출 실패: {exc}") from exc

    def answer_question(
        self,
        title: str,
        summary_context: str,
        paper_excerpt: str,
        question: str,
        history: List[ChatMessage],
    ) -> str:
        system_prompt = (
            f"{QA_SYSTEM_PROMPT}\n\n"
            f"[대상 논문 제목]\n{title}\n\n"
            f"[사전 분석 요약]\n{summary_context}\n\n"
            f"[논문 원문 발췌]\n{paper_excerpt[:8000]}"
        )
        messages = [
            {"role": msg.role, "content": msg.content} for msg in history[-6:]
        ]
        messages.append({"role": "user", "content": question})

        try:
            response = self._client.messages.create(
                model=self.model_name,
                max_tokens=1024,
                temperature=0.4,
                system=system_prompt,
                messages=messages,
            )
            parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]
            return "\n".join(parts).strip()
        except Exception as exc:
            raise LLMServiceError(f"Anthropic Q&A 호출 실패: {exc}") from exc


class LLMService:
    """환경변수(LLM_PROVIDER)에 따라 적절한 LLM 제공자를 선택해 실행하는 파사드 서비스."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._provider = provider

    def _get_provider(self) -> BaseLLMProvider:
        """필요 시점에 환경변수 기반 Provider 인스턴스를 지연 생성합니다."""
        if self._provider is not None:
            return self._provider

        if self._settings.llm_provider == "anthropic":
            self._provider = AnthropicProvider(
                api_key=self._settings.anthropic_api_key,
                model=self._settings.anthropic_model,
            )
        else:
            self._provider = OpenAIProvider(
                api_key=self._settings.openai_api_key,
                model=self._settings.openai_model,
            )
        return self._provider

    @property
    def provider_name(self) -> str:
        return self._get_provider().provider_name

    @property
    def model_name(self) -> str:
        return self._get_provider().model_name

    def analyze_paper(self, title: str, paper_text: str) -> PaperAnalysisLLMOutput:
        """논문 텍스트를 입력받아 검증된 입문자용 분석 결과를 반환합니다."""
        if not paper_text or not paper_text.strip():
            raise LLMServiceError("분석할 논문 텍스트가 비어 있습니다.")

        provider = self._get_provider()
        result = provider.generate_structured_analysis(title=title, paper_text=paper_text)
        # 최종 방어적 Pydantic 검증
        return PaperAnalysisLLMOutput.model_validate(result.model_dump())

    def answer_question(
        self,
        title: str,
        summary_context: str,
        paper_excerpt: str,
        question: str,
        history: Optional[List[ChatMessage]] = None,
    ) -> str:
        """분석된 논문에 대한 초보자 추가 질문에 답변합니다."""
        provider = self._get_provider()
        return provider.answer_question(
            title=title,
            summary_context=summary_context,
            paper_excerpt=paper_excerpt,
            question=question,
            history=history or [],
        )
