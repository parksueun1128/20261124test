import type {
  ArxivCategory,
  ChatMessage,
  LatestPapersResponse,
  PaperAnalysisResponse,
  PaperQAResponse,
} from "../types/paper";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `요청 처리 중 오류가 발생했습니다. (HTTP ${response.status})`;
    try {
      const errorData = await response.json();
      if (typeof errorData?.detail === "string" && errorData.detail.trim()) {
        message = errorData.detail;
      }
    } catch {
      // JSON 파싱 불가 시 기본 에러 메시지 유지
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

/** arXiv 최신 AI 논문 목록을 조회합니다. */
export async function fetchLatestPapers(params?: {
  category?: ArxivCategory;
  query?: string;
  maxResults?: number;
}): Promise<LatestPapersResponse> {
  const searchParams = new URLSearchParams();
  if (params?.category && params.category !== "all") {
    searchParams.set("category", params.category);
  }
  if (params?.query && params.query.trim()) {
    searchParams.set("query", params.query.trim());
  }
  if (params?.maxResults) {
    searchParams.set("max_results", String(params.maxResults));
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/api/papers/latest${queryString ? `?${queryString}` : ""}`;

  try {
    const response = await fetch(url);
    return await handleResponse<LatestPapersResponse>(response);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      "백엔드 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인해 주세요.",
      0
    );
  }
}

/** DB에 캐싱된 기존 분석 이력을 불러옵니다. */
export async function fetchAnalysisHistory(): Promise<PaperAnalysisResponse[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/papers/history`);
    return await handleResponse<PaperAnalysisResponse[]>(response);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError("분석 이력을 불러오는 중 네트워크 오류가 발생했습니다.", 0);
  }
}

/** arXiv ID 또는 URL을 기반으로 초보자 맞춤 논문 분석을 요청합니다. */
export async function analyzePaperByArxivId(
  arxivId: string,
  forceRefresh = false
): Promise<PaperAnalysisResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/papers/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        arxiv_id: arxivId,
        force_refresh: forceRefresh,
      }),
    });
    return await handleResponse<PaperAnalysisResponse>(response);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      "논문 분석 요청 중 서버와 연결이 끊어졌습니다. 잠시 후 다시 시도해 주세요.",
      0
    );
  }
}

/** 사용자가 직접 업로드한 PDF 파일을 분석합니다. */
export async function analyzePaperByPdf(
  file: File,
  forceRefresh = false
): Promise<PaperAnalysisResponse> {
  const formData = new FormData();
  formData.append("pdf_file", file);
  formData.append("force_refresh", String(forceRefresh));

  try {
    const response = await fetch(`${API_BASE_URL}/api/papers/analyze`, {
      method: "POST",
      body: formData,
    });
    return await handleResponse<PaperAnalysisResponse>(response);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      "PDF 업로드 분석 중 네트워크 오류가 발생했습니다. 파일 크기와 서버 상태를 확인해 주세요.",
      0
    );
  }
}

/** 분석 완료된 논문에 대해 초보자 추가 질문을 전송합니다. */
export async function askPaperQuestion(
  arxivId: string,
  question: string,
  history: ChatMessage[]
): Promise<PaperQAResponse> {
  const encodedId = arxivId
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");

  try {
    const response = await fetch(`${API_BASE_URL}/api/papers/${encodedId}/qa`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        history,
      }),
    });
    return await handleResponse<PaperQAResponse>(response);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError("질문 전송 중 네트워크 오류가 발생했습니다.", 0);
  }
}
