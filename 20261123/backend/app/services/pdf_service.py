"""PDF 다운로드, 텍스트 추출(PyMuPDF) 및 핵심 섹션 우선 청킹 서비스."""

import hashlib
import re
from typing import Optional, Tuple

import fitz  # PyMuPDF
import httpx


class PDFServiceError(Exception):
    """PDF 다운로드 또는 텍스트 추출 실패 시 발생하는 예외."""


# 영문 논문에서 주요 섹션 헤더를 탐지하기 위한 정규표현식
_SECTION_HEADER_RE = re.compile(
    r"(?im)^(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(abstract|introduction|background|related work|method|methodology|"
    r"approach|experiments?|results?|discussion|conclusion|conclusions|limitations)\b[:.\s]*$"
)


class PDFService:
    """PDF 원문에서 텍스트를 추출하고 LLM 컨텍스트 한도에 맞게 핵심 섹션을 선별합니다."""

    def __init__(self, max_chars: int = 18000) -> None:
        self.max_chars = max_chars

    @staticmethod
    def compute_pdf_cache_key(pdf_bytes: bytes) -> str:
        """동일한 PDF 재업로드 시 DB 캐시를 적중시키기 위한 SHA-256 기반 고유 키를 생성합니다."""
        digest = hashlib.sha256(pdf_bytes).hexdigest()[:16]
        return f"pdf:{digest}"

    def download_pdf(self, pdf_url: str, timeout: float = 25.0) -> bytes:
        """arXiv 등 원격 URL에서 PDF 바이너리를 다운로드합니다."""
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": "EasyPaperAI/1.0 (+https://arxiv.org)"},
            ) as client:
                response = client.get(pdf_url)
                response.raise_for_status()
                content = response.content
        except Exception as exc:
            raise PDFServiceError(f"PDF 다운로드에 실패했습니다: {exc}") from exc

        if not content or len(content) < 100:
            raise PDFServiceError("다운로드된 PDF 파일이 비어 있거나 손상되었습니다.")
        return content

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> Tuple[str, Optional[str]]:
        """PyMuPDF(fitz)를 사용하여 PDF 바이트에서 전체 텍스트와 추정 제목을 추출합니다."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            raise PDFServiceError(
                f"PDF 파일을 열 수 없습니다. 올바른 PDF 파일인지 확인해 주세요: {exc}"
            ) from exc

        try:
            if doc.page_count == 0:
                raise PDFServiceError("페이지가 없는 빈 PDF 파일입니다.")

            # PDF 메타데이터에서 제목 추출 시도
            meta_title = (doc.metadata or {}).get("title") or ""
            meta_title = re.sub(r"\s+", " ", meta_title).strip()

            pages_text = []
            for page in doc:
                text = page.get_text("text")
                if text:
                    pages_text.append(text)

            full_text = "\n\n".join(pages_text).strip()
            if not full_text:
                raise PDFServiceError(
                    "PDF에서 추출 가능한 텍스트가 없습니다. (스캔 이미지 전용 PDF일 수 있습니다.)"
                )

            # 메타데이터 제목이 없거나 의미 없는 경우 첫 페이지 상단 문장을 제목으로 추정
            inferred_title = meta_title if len(meta_title) >= 5 else self._infer_title(full_text)
            return full_text, inferred_title
        finally:
            doc.close()

    @staticmethod
    def _infer_title(full_text: str) -> Optional[str]:
        """본문 첫 부분의 의미 있는 첫 줄을 논문 제목 후보로 추출합니다."""
        for line in full_text.splitlines()[:15]:
            cleaned = re.sub(r"\s+", " ", line).strip()
            if 10 <= len(cleaned) <= 220 and not cleaned.lower().startswith("arxiv:"):
                return cleaned
        return None

    def extract_key_sections(self, full_text: str, max_chars: Optional[int] = None) -> str:
        """LLM 토큰 한도를 초과하지 않도록 초록·서론·결론 중심으로 핵심 텍스트를 구성합니다.

        텍스트 청킹/축약 전략:
        1. 전체 텍스트가 max_chars 이하이면 불필요한 공백만 정리해 그대로 반환합니다.
        2. 논문 섹션 헤더(Abstract, Introduction, Conclusion 등)가 감지되면
           초록(Abstract) -> 서론(Introduction) -> 결론(Conclusion) 순으로 우선 배치하고,
           남은 문자 예산에 앞부분 본문을 채워 넣습니다.
        3. 섹션 구분이 불명확한 PDF는 앞부분 75%(초록·서론·핵심 방법론)와
           뒷부분 25%(실험 결론)를 결합해 잘라냅니다.
        """
        budget = max_chars or self.max_chars
        normalized = re.sub(r"[ \t]+", " ", full_text)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()

        if len(normalized) <= budget:
            return normalized

        # 1) 섹션 헤더 위치 탐색
        matches = list(_SECTION_HEADER_RE.finditer(normalized))
        sections: dict[str, str] = {}

        if matches:
            for idx, match in enumerate(matches):
                header_name = match.group(1).lower()
                start = match.start()
                end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
                snippet = normalized[start:end].strip()

                # 동일 계열 섹션명 정규화
                if header_name == "abstract" and "abstract" not in sections:
                    sections["abstract"] = snippet
                elif header_name == "introduction" and "introduction" not in sections:
                    sections["introduction"] = snippet
                elif header_name in ("conclusion", "conclusions", "discussion") and "conclusion" not in sections:
                    sections["conclusion"] = snippet

        # 2) 핵심 섹션이 2개 이상 식별된 경우 우선 조합
        if len(sections) >= 2:
            priority_parts = []
            # 각 핵심 섹션별 예산 할당 (초록 15%, 서론 40%, 결론 25%, 나머지 앞부분 20%)
            if "abstract" in sections:
                priority_parts.append(sections["abstract"][: int(budget * 0.15)])
            if "introduction" in sections:
                priority_parts.append(sections["introduction"][: int(budget * 0.40)])
            if "conclusion" in sections:
                priority_parts.append(sections["conclusion"][: int(budget * 0.25)])

            combined = "\n\n---\n\n".join(priority_parts)
            remaining = budget - len(combined) - 80
            if remaining > 500:
                lead_excerpt = normalized[:remaining].strip()
                combined = f"[논문 도입부 발췌]\n{lead_excerpt}\n\n---\n\n{combined}"

            return combined[:budget] + "\n\n[... 토큰 한도 보호를 위해 일부 본문 생략 ...]"

        # 3) 폴백 전략: 앞부분 75% + 뒷부분 25% 조합 (참고문헌 직전 결론부 보존)
        head_len = int(budget * 0.75)
        tail_len = budget - head_len - 80
        head_part = normalized[:head_len].rstrip()
        tail_part = normalized[-tail_len:].lstrip() if tail_len > 0 else ""

        return (
            f"{head_part}\n\n"
            "[... 중간 세부 수식/실험 섹션 생략 ...]\n\n"
            f"{tail_part}"
        )
