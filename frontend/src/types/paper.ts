export type DifficultyLevel = "입문" | "중급" | "심화";

export type ArxivCategory = "all" | "cs.AI" | "cs.LG" | "cs.CL";

export interface GlossaryItem {
  term: string;
  definition: string;
}

export interface PaperSummaryItem {
  arxiv_id: string;
  title: string;
  authors: string[];
  published_at: string;
  categories: string[];
  summary: string;
  pdf_url: string;
  arxiv_url: string;
  is_analyzed: boolean;
}

export interface LatestPapersResponse {
  category: string;
  total: number;
  papers: PaperSummaryItem[];
}

export interface PaperAnalysisResponse {
  arxiv_id: string;
  title: string;
  one_line_summary: string;
  easy_explanation: string;
  key_contributions: string[];
  glossary: GlossaryItem[];
  difficulty_level: DifficultyLevel;
  authors: string[];
  published_at?: string | null;
  pdf_url?: string | null;
  source_type: "arxiv" | "pdf";
  cached: boolean;
  analyzed_at?: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface PaperQAResponse {
  arxiv_id: string;
  answer: string;
}
