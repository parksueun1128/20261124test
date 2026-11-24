import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

interface AnalysisSkeletonProps {
  targetLabel: string;
}

const PROGRESS_STEPS = [
  "1/3 · 논문 원문과 초록을 수집하고 있습니다...",
  "2/3 · 토큰 한도에 맞춰 초록·서론·결론 핵심 섹션을 추출 중입니다...",
  "3/3 · AI 튜터가 일상 비유와 용어 사전을 작성하고 있습니다... (5~15초 소요)",
];

export function AnalysisSkeleton({ targetLabel }: AnalysisSkeletonProps) {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStepIndex((prev) => (prev < PROGRESS_STEPS.length - 1 ? prev + 1 : prev));
    }, 3200);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-indigo-200 bg-indigo-50/70 p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-indigo-600 text-white">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
          <div>
            <p className="flex items-center gap-1.5 text-sm font-bold text-indigo-900">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              입문자 맞춤 논문 분석 진행 중
            </p>
            <p className="mt-0.5 text-xs text-indigo-700">{targetLabel}</p>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          {PROGRESS_STEPS.map((label, idx) => {
            const active = idx === stepIndex;
            const completed = idx < stepIndex;
            return (
              <div
                key={label}
                className={`flex items-center gap-2.5 text-sm transition ${
                  active
                    ? "font-semibold text-indigo-900"
                    : completed
                      ? "text-emerald-700"
                      : "text-slate-400"
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    active
                      ? "animate-pulse bg-indigo-600"
                      : completed
                        ? "bg-emerald-500"
                        : "bg-slate-300"
                  }`}
                />
                {label}
              </div>
            );
          })}
        </div>
      </div>

      {/* 스켈레톤 카드 프리뷰 */}
      <div className="animate-pulse space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <div className="h-4 w-28 rounded bg-slate-200" />
          <div className="mt-3 h-7 w-3/4 rounded bg-slate-200" />
          <div className="mt-4 h-16 rounded-xl bg-indigo-50" />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-6">
            <div className="h-5 w-36 rounded bg-slate-200" />
            <div className="mt-4 space-y-2.5">
              <div className="h-4 w-full rounded bg-slate-100" />
              <div className="h-4 w-11/12 rounded bg-slate-100" />
              <div className="h-4 w-5/6 rounded bg-slate-100" />
              <div className="h-4 w-full rounded bg-slate-100" />
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6">
            <div className="h-5 w-32 rounded bg-slate-200" />
            <div className="mt-4 space-y-3">
              <div className="h-12 rounded-xl bg-slate-100" />
              <div className="h-12 rounded-xl bg-slate-100" />
              <div className="h-12 rounded-xl bg-slate-100" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
