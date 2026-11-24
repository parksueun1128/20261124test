import { Calendar, CheckCircle2, ExternalLink, Sparkles, Users } from "lucide-react";
import type { PaperSummaryItem } from "../types/paper";

interface PaperCardProps {
  paper: PaperSummaryItem;
  onSelect: (paper: PaperSummaryItem) => void;
}

export function PaperCard({ paper, onSelect }: PaperCardProps) {
  const authorDisplay =
    paper.authors.length > 3
      ? `${paper.authors.slice(0, 3).join(", ")} 외 ${paper.authors.length - 3}명`
      : paper.authors.join(", ");

  return (
    <article className="group flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            {paper.categories.slice(0, 3).map((cat) => (
              <span
                key={cat}
                className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600"
              >
                {cat}
              </span>
            ))}
            <span className="font-mono text-xs text-slate-400">
              {paper.arxiv_id}
            </span>
          </div>

          {paper.is_analyzed && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
              <CheckCircle2 className="h-3.5 w-3.5" />
              캐시됨
            </span>
          )}
        </div>

        <h3 className="mt-3 text-base font-bold leading-snug text-slate-900 group-hover:text-indigo-700">
          {paper.title}
        </h3>

        <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1">
            <Users className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate max-w-[220px]">{authorDisplay || "저자 미상"}</span>
          </span>
          {paper.published_at && (
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 shrink-0" />
              {paper.published_at}
            </span>
          )}
        </div>

        <p className="line-clamp-3 mt-3 text-sm leading-relaxed text-slate-600">
          {paper.summary}
        </p>
      </div>

      <div className="mt-5 flex items-center justify-between gap-2 border-t border-slate-100 pt-4">
        <a
          href={paper.arxiv_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 transition hover:text-slate-900"
        >
          arXiv 원문
          <ExternalLink className="h-3.5 w-3.5" />
        </a>

        <button
          type="button"
          onClick={() => onSelect(paper)}
          className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-600 hover:text-white"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {paper.is_analyzed ? "해설 바로 보기" : "쉽게 분석하기"}
        </button>
      </div>
    </article>
  );
}
