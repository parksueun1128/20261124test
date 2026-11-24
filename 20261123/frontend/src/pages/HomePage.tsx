import { useCallback, useEffect, useState } from "react";
import { BookOpen, Clock, Database } from "lucide-react";
import {
  analyzePaperByArxivId,
  analyzePaperByPdf,
  fetchAnalysisHistory,
  fetchLatestPapers,
} from "../api/paperApi";
import { AnalysisSkeleton } from "../components/AnalysisSkeleton";
import { AnalysisViewer } from "../components/AnalysisViewer";
import { CategoryFilter } from "../components/CategoryFilter";
import { CustomPaperInput } from "../components/CustomPaperInput";
import { ErrorBanner } from "../components/ErrorBanner";
import { Header } from "../components/Header";
import { PaperCard } from "../components/PaperCard";
import type {
  ArxivCategory,
  PaperAnalysisResponse,
  PaperSummaryItem,
} from "../types/paper";

export function HomePage() {
  const [activeView, setActiveView] = useState<"feed" | "history">("feed");
  const [category, setCategory] = useState<ArxivCategory>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const [papers, setPapers] = useState<PaperSummaryItem[]>([]);
  const [history, setHistory] = useState<PaperAnalysisResponse[]>([]);
  const [feedLoading, setFeedLoading] = useState(true);
  const [feedError, setFeedError] = useState<string | null>(null);

  const [selectedAnalysis, setSelectedAnalysis] =
    useState<PaperAnalysisResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzingTarget, setAnalyzingTarget] = useState("");
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const loadLatestPapers = useCallback(
    async (targetCat: ArxivCategory, targetQuery: string) => {
      setFeedLoading(true);
      setFeedError(null);
      try {
        const data = await fetchLatestPapers({
          category: targetCat,
          query: targetQuery,
          maxResults: 12,
        });
        setPapers(data.papers);
      } catch (err) {
        setFeedError(
          err instanceof Error
            ? err.message
            : "최신 논문 목록을 불러오지 못했습니다."
        );
      } finally {
        setFeedLoading(false);
      }
    },
    []
  );

  const loadHistory = useCallback(async () => {
    try {
      const items = await fetchAnalysisHistory();
      setHistory(items);
    } catch {
      // 초기 이력 조회 실패는 메인 피드 UX를 방해하지 않도록 조용히 무시
    }
  }, []);

  useEffect(() => {
    void loadLatestPapers(category, searchQuery);
  }, [category, searchQuery, loadLatestPapers]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const markPaperAsAnalyzed = (result: PaperAnalysisResponse) => {
    setPapers((prev) =>
      prev.map((item) =>
        item.arxiv_id === result.arxiv_id ? { ...item, is_analyzed: true } : item
      )
    );
    setHistory((prev) => {
      const filtered = prev.filter((item) => item.arxiv_id !== result.arxiv_id);
      return [result, ...filtered];
    });
  };

  const handleAnalyzeArxiv = async (
    arxivIdOrUrl: string,
    label?: string,
    forceRefresh = false
  ) => {
    setAnalyzing(true);
    setAnalyzingTarget(label || arxivIdOrUrl);
    setAnalysisError(null);
    setSelectedAnalysis(null);
    window.scrollTo({ top: 0, behavior: "smooth" });

    try {
      const result = await analyzePaperByArxivId(arxivIdOrUrl, forceRefresh);
      setSelectedAnalysis(result);
      markPaperAsAnalyzed(result);
    } catch (err) {
      setAnalysisError(
        err instanceof Error
          ? err.message
          : "논문 분석 중 알 수 없는 오류가 발생했습니다."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAnalyzePdf = async (file: File) => {
    setAnalyzing(true);
    setAnalyzingTarget(`PDF 파일: ${file.name}`);
    setAnalysisError(null);
    setSelectedAnalysis(null);
    window.scrollTo({ top: 0, behavior: "smooth" });

    try {
      const result = await analyzePaperByPdf(file, false);
      setSelectedAnalysis(result);
      markPaperAsAnalyzed(result);
    } catch (err) {
      setAnalysisError(
        err instanceof Error
          ? err.message
          : "PDF 분석 중 오류가 발생했습니다."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const handleBackToList = () => {
    setSelectedAnalysis(null);
    setAnalysisError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Header
        activeView={activeView}
        historyCount={history.length}
        onChangeView={(view) => {
          setActiveView(view);
          setSelectedAnalysis(null);
          setAnalysisError(null);
        }}
        onGoHome={() => {
          setActiveView("feed");
          setSelectedAnalysis(null);
          setAnalysisError(null);
        }}
      />

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6 sm:py-8">
        {analysisError && (
          <ErrorBanner
            message={analysisError}
            onDismiss={() => setAnalysisError(null)}
          />
        )}

        {/* 상태 1: 논문 분석 진행 중 스켈레톤 */}
        {analyzing ? (
          <AnalysisSkeleton targetLabel={analyzingTarget} />
        ) : selectedAnalysis ? (
          /* 상태 2: 분석 결과 뷰어 */
          <AnalysisViewer
            analysis={selectedAnalysis}
            onBack={handleBackToList}
            onReanalyze={(id) =>
              void handleAnalyzeArxiv(id, selectedAnalysis.title, true)
            }
          />
        ) : (
          /* 상태 3: 대시보드 (직접 입력 + 최신 피드 또는 분석 캐시 이력) */
          <>
            <CustomPaperInput
              disabled={analyzing}
              onAnalyzeArxiv={(val) => void handleAnalyzeArxiv(val)}
              onAnalyzePdf={(file) => void handleAnalyzePdf(file)}
            />

            {activeView === "feed" ? (
              <section className="space-y-5">
                <CategoryFilter
                  selectedCategory={category}
                  searchQuery={searchQuery}
                  loading={feedLoading}
                  onSelectCategory={setCategory}
                  onSearch={setSearchQuery}
                  onRefresh={() => void loadLatestPapers(category, searchQuery)}
                />

                {feedError && (
                  <ErrorBanner
                    message={feedError}
                    onRetry={() => void loadLatestPapers(category, searchQuery)}
                  />
                )}

                {feedLoading ? (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {Array.from({ length: 6 }).map((_, idx) => (
                      <div
                        key={idx}
                        className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5"
                      >
                        <div className="h-4 w-24 rounded bg-slate-200" />
                        <div className="mt-3 h-5 w-full rounded bg-slate-200" />
                        <div className="mt-2 h-5 w-4/5 rounded bg-slate-200" />
                        <div className="mt-4 space-y-2">
                          <div className="h-3.5 w-full rounded bg-slate-100" />
                          <div className="h-3.5 w-11/12 rounded bg-slate-100" />
                          <div className="h-3.5 w-2/3 rounded bg-slate-100" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : papers.length === 0 ? (
                  <div className="rounded-2xl border border-slate-200 bg-white py-14 text-center">
                    <BookOpen className="mx-auto h-10 w-10 text-slate-300" />
                    <p className="mt-3 text-sm font-semibold text-slate-700">
                      조건에 맞는 최신 논문이 없습니다.
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      다른 카테고리를 선택하거나 검색 키워드를 변경해 보세요.
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {papers.map((paper) => (
                      <PaperCard
                        key={paper.arxiv_id}
                        paper={paper}
                        onSelect={(selected) =>
                          void handleAnalyzeArxiv(selected.arxiv_id, selected.title)
                        }
                      />
                    ))}
                  </div>
                )}
              </section>
            ) : (
              /* 분석 완료 캐시 이력 탭 */
              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                    <Database className="h-5 w-5 text-indigo-600" />
                    DB에 캐싱된 논문 해설 ({history.length})
                  </h2>
                </div>

                {history.length === 0 ? (
                  <div className="rounded-2xl border border-slate-200 bg-white py-14 text-center">
                    <Clock className="mx-auto h-10 w-10 text-slate-300" />
                    <p className="mt-3 text-sm font-semibold text-slate-700">
                      아직 분석 완료된 논문이 없습니다.
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      최신 논문 카드를 클릭하거나 PDF를 업로드하면 결과가 자동으로 캐싱됩니다.
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2">
                    {history.map((item) => (
                      <button
                        key={item.arxiv_id}
                        type="button"
                        onClick={() =>
                          setSelectedAnalysis({ ...item, cached: true })
                        }
                        className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-indigo-300 hover:shadow-md"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs text-slate-400">
                            {item.arxiv_id}
                          </span>
                          <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
                            {item.difficulty_level}
                          </span>
                        </div>
                        <h3 className="mt-2 text-base font-bold text-slate-900">
                          {item.title}
                        </h3>
                        <p className="mt-2 text-sm text-slate-600">
                          {item.one_line_summary}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
