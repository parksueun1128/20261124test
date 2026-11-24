# EasyPaper AI — AI 입문자를 위한 논문 해설 풀스택 웹 앱 (MVP)

arXiv의 최신 AI 논문(`cs.AI`, `cs.LG`, `cs.CL`)을 수집하거나 사용자가 입력한 arXiv URL / PDF 파일을 파싱하여 **한 줄 핵심 요약, 일상 비유 기반 설명, 기존 대비 핵심 기여, AI 용어 사전, 초보자 Q&A 챗봇, Markdown 내보내기**를 제공하는 풀스택 애플리케이션입니다.

## 주요 기능
- **최신 AI 논문 피드 (`GET /api/papers/latest`)**: `cs.AI`, `cs.LG`, `cs.CL` 카테고리 필터링 및 키워드 검색 지원
- **초보자 맞춤 논문 분석 (`POST /api/papers/analyze`)**:
  - arXiv ID/URL 또는 직접 PDF 업로드(`.pdf`) 지원
  - SQLite(SQLAlchemy 2.0 ORM, PostgreSQL 전환 호환) 기반 분석 결과 캐싱으로 중복 LLM 호출 방지
  - PyMuPDF 기반 텍스트 추출 + 초록·서론·결론 핵심 섹션 우선 청킹(토큰 초과 방지)
  - OpenAI Structured Outputs / Anthropic Claude Tool-Use 강제 JSON 스키마 + Pydantic v2 검증
- **초보자 Q&A 챗봇 (`POST /api/papers/{arxiv_id}/qa`)**: 분석된 논문에 대한 추가 질문 응답
- **Markdown 내보내기**: 분석 결과를 `.md` 파일로 즉시 다운로드

## 로컬 실행 방법

### 1. 백엔드 실행 (Python 3.11+)
```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# .env 파일에 OPENAI_API_KEY (또는 ANTHROPIC_API_KEY) 입력

uvicorn app.main:app --reload --port 8000
```

### 2. 프론트엔드 실행 (Node.js 18+)
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
브라우저에서 `http://localhost:5173`으로 접속합니다. (FastAPI Swagger 문서: `http://localhost:8000/docs`)

### 3. 백엔드 단위 테스트 실행
```bash
cd backend
pytest -v
```
