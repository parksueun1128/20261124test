import { useState } from "react";
import {
  ArrowLeft,
  Award,
  BookMarked,
  Database,
  Download,
  ExternalLink,
  Lightbulb,
  MessageCircleQuestion,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import type { DifficultyLevel, PaperAnalysisResponse } from "../types/paper";
import { downloadPaperMarkdown } from "../utils/markdown";
import { PaperQAChat } from "./PaperQAChat";

interface AnalysisViewerProps {
  analysis: PaperAnalysisResponse;
  onBack: () => void;
  onReanalyze?: (arxivId: string) => void;
}

type ViewerTab = "all" | "explanation" | "contributions" | "glossary" | "qa";

const DIFFICULTY_STYLES: Record<DifficultyLevel, string> = {
  입문: "bg-emerald-100 text-emerald-800 border-emerald-200",
  중급: "bg-amber-100 text-amber-800 border-amber-200",
  심화: "bg-rose-100 text-rose-800 border-rose-200",
};

export function AnalysisViewer({
  analysis,
  onBack,
  onReanalyze,
}: AnalysisViewerProps) {
  const [activeTab, setActiveTab] = useState<ViewerTab>("all");

  const paragraphs = analysis.easy_explanation
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  const tabs: { id: ViewerTab; label: string }[] = [
    { id: "all", label: "전체 보기" },
    { id: "explanation", label: "쉬운 비유 설명" },
    { id: "contributions", label: `핵심 기여 (${analysis.key_contributions.length})` },
    { id: "glossary", label: `용어 사전 (${analysis.glossary.length})` },
    { id: "qa", label: "초보자 Q&A" },
  ];

  return (
    <div className="space-y-6">
      {/* 상단 액션 바 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 hover:text-slate-900"
        >
          <ArrowLeft className="h-4 w-4" />
          목록으로 돌아가기
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => downloadPaperMarkdown(analysis)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:border-indigo-300 hover:text-indigo-700"
          >
            <Download className="h-4 w-4" />
            Markdown 내보내기
          </button>

          {analysis.pdf_url && (
            <a
              href={analysis.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              원문 PDF
              <ExternalLink className="h-4 w-4" />
            </a>
          )}

          {analysis.source_type === "arxiv" && onReanalyze && (
            <button
              type="button"
              onClick={() => onReanalyze(analysis.arxiv_id)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              다시 분석
            </button>
          )}
        </div>
      </div>

      {/* 논문 헤더 + 한 줄 요약 배너 */}
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full border px-2.5 py-0.5 text-xs font-bold ${
              DIFFICULTY_STYLES[analysis.difficulty_level]
            }`}
          >
            난이도 · {analysis.difficulty_level}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 font-mono text-xs text-slate-600">
            {analysis.arxiv_id}
          </span>
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
              analysis.cached
                ? "bg-emerald-50 text-emerald-700"
                : "bg-indigo-50 text-indigo-700"
            }`}
          >
            <Database className="h-3 w-3" />
            {analysis.cached ? "DB 캐시에서 즉시 로드됨" : "신규 AI 분석 완료"}
          </span>
        </div>

        <h2 className="mt-3 text-2xl font-extrabold leading-tight text-slate-900">
          {analysis.title}
        </h2>

        {(analysis.authors.length > 0 || analysis.published_at) && (
          <p className="mt-2 text-xs text-slate-500">
            {analysis.authors.slice(0, 5).join(", ")}
            {analysis.authors.length > 5 && ` 외 ${analysis.authors.length - 5}명`}
            {analysis.published_at && ` · 발행일 ${analysis.published_at}`}
          </p>
        )}

        {/* 한 줄 핵심 요약 */}
        <div className="mt-5 rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50 to-sky-50 p-4 sm:p-5">
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-indigo-700">
            <Sparkles className="h-4 w-4" />한 줄 핵심 요약
          </div>
          <p className="mt-1.5 text-base font-bold leading-relaxed text-slate-900 sm:text-lg">
            {analysis.one_line_summary}
          </p>
        </div>

        {/* 섹션 탭 바 */}
        <div className="mt-5 flex flex-wrap gap-1.5 border-t border-slate-100 pt-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-xl px-3.5 py-1.5 text-sm font-medium transition ${
                activeTab === tab.id
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </section>

      {/* 쉬운 비유 설명 */}
      {(activeTab === "all" || activeTab === "explanation") && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-amber-500" />
            <h3 className="text-lg font-bold text-slate-900">
              비전공자를 위한 쉬운 비유 설명
            </h3>
          </div>
          <div className="mt-4 space-y-4 text-[15px] leading-7 text-slate-700">
            {paragraphs.map((paragraph, idx) => (
              <p key={idx}>{paragraph}</p>
            ))}
          </div>
        </section>
      )}

      {/* 핵심 기여 */}
      {(activeTab === "all" || activeTab === "contributions") && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <Award className="h-5 w-5 text-indigo-600" />
            <h3 className="text-lg font-bold text-slate-900">
              이 논문의 핵심 기여 (기존 대비 개선점)
            </h3>
          </div>
          <ul className="mt-4 space-y-3">
            {analysis.key_contributions.map((item, idx) => (
              <li
                key={idx}
                className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50/80 p-4"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                  {idx + 1}
                </span>
                <p className="text-sm leading-relaxed text-slate-800">{item}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* AI 용어 사전 */}
      {(activeTab === "all" || activeTab === "glossary") && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <BookMarked className="h-5 w-5 text-emerald-600" />
            <h3 className="text-lg font-bold text-slate-900">
              논문 속 어려운 AI 용어 사전
            </h3>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {analysis.glossary.map((entry, idx) => (
              <div
                key={`${entry.term}-${idx}`}
                className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4"
              >
                <dt className="text-sm font-bold text-emerald-950">
                  {entry.term}
                </dt>
                <dd className="mt-1.5 text-sm leading-relaxed text-slate-700">
                  {entry.definition}
                </dd>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 초보자 Q&A 챗봇 */}
      {(activeTab === "all" || activeTab === "qa") && (
        <section>
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-500">
            <MessageCircleQuestion className="h-4 w-4" />
            추가 학습 도우미
          </div>
          <PaperQAChat key={analysis.arxiv_id} arxivId={analysis.arxiv_id} />
        </section>
      )}
    </div>
  );
}
