import { FormEvent, useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import type { ArxivCategory } from "../types/paper";

interface CategoryFilterProps {
  selectedCategory: ArxivCategory;
  searchQuery: string;
  loading: boolean;
  onSelectCategory: (category: ArxivCategory) => void;
  onSearch: (query: string) => void;
  onRefresh: () => void;
}

const CATEGORIES: { value: ArxivCategory; label: string; desc: string }[] = [
  { value: "all", label: "전체 AI", desc: "AI · ML · NLP" },
  { value: "cs.AI", label: "cs.AI", desc: "인공지능" },
  { value: "cs.LG", label: "cs.LG", desc: "머신러닝" },
  { value: "cs.CL", label: "cs.CL", desc: "자연어처리" },
];

export function CategoryFilter({
  selectedCategory,
  searchQuery,
  loading,
  onSelectCategory,
  onSearch,
  onRefresh,
}: CategoryFilterProps) {
  const [draftQuery, setDraftQuery] = useState(searchQuery);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSearch(draftQuery.trim());
  };

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        {CATEGORIES.map((cat) => {
          const active = selectedCategory === cat.value;
          return (
            <button
              key={cat.value}
              type="button"
              onClick={() => onSelectCategory(cat.value)}
              className={`rounded-xl border px-3.5 py-2 text-sm font-medium transition ${
                active
                  ? "border-indigo-600 bg-indigo-600 text-white shadow-sm"
                  : "border-slate-200 bg-white text-slate-700 hover:border-indigo-300 hover:text-indigo-700"
              }`}
            >
              <span>{cat.label}</span>
              <span
                className={`ml-1.5 text-xs ${
                  active ? "text-indigo-100" : "text-slate-400"
                }`}
              >
                {cat.desc}
              </span>
            </button>
          );
        })}
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <div className="relative flex-1 sm:w-64">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={draftQuery}
            onChange={(e) => setDraftQuery(e.target.value)}
            placeholder="영문 키워드 검색 (예: RAG, Agent)"
            className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-slate-900 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-60"
        >
          검색
        </button>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          title="최신 논문 새로고침"
          className="rounded-xl border border-slate-200 bg-white p-2 text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </form>
    </div>
  );
}
