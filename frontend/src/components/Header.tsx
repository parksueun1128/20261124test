import { BookOpenCheck, History, Sparkles } from "lucide-react";

interface HeaderProps {
  activeView: "feed" | "history";
  historyCount: number;
  onChangeView: (view: "feed" | "history") => void;
  onGoHome: () => void;
}

export function Header({
  activeView,
  historyCount,
  onChangeView,
  onGoHome,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 sm:px-6">
        <button
          type="button"
          onClick={onGoHome}
          className="flex items-center gap-2.5 text-left transition hover:opacity-85"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-900">
              EasyPaper AI
            </h1>
            <p className="hidden text-xs text-slate-500 sm:block">
              AI 입문자를 위한 최신 논문 쉬운 해설 &amp; 용어 사전
            </p>
          </div>
        </button>

        <nav className="flex items-center gap-1.5 rounded-xl bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => onChangeView("feed")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              activeView === "feed"
                ? "bg-white text-indigo-700 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <BookOpenCheck className="h-4 w-4" />
            최신 논문
          </button>
          <button
            type="button"
            onClick={() => onChangeView("history")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              activeView === "history"
                ? "bg-white text-indigo-700 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <History className="h-4 w-4" />
            분석 캐시
            {historyCount > 0 && (
              <span className="rounded-full bg-indigo-100 px-1.5 py-0.5 text-xs font-semibold text-indigo-700">
                {historyCount}
              </span>
            )}
          </button>
        </nav>
      </div>
    </header>
  );
}
