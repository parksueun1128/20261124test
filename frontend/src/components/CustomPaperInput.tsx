import { FormEvent, useRef, useState } from "react";
import { FileUp, Link2, Sparkles, UploadCloud } from "lucide-react";

interface CustomPaperInputProps {
  disabled?: boolean;
  onAnalyzeArxiv: (arxivIdOrUrl: string) => void;
  onAnalyzePdf: (file: File) => void;
}

const SAMPLE_PAPERS = [
  { id: "1706.03762", label: "Transformer 원조 논문 (1706.03762)" },
  { id: "2005.11401", label: "RAG 개념 논문 (2005.11401)" },
];

export function CustomPaperInput({
  disabled = false,
  onAnalyzeArxiv,
  onAnalyzePdf,
}: CustomPaperInputProps) {
  const [mode, setMode] = useState<"url" | "pdf">("url");
  const [inputValue, setInputValue] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleSubmitUrl = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = inputValue.trim();
    if (!trimmed) {
      setLocalError("arXiv ID 또는 논문 URL을 입력해 주세요.");
      return;
    }
    setLocalError(null);
    onAnalyzeArxiv(trimmed);
  };

  const handleSelectedFile = (file: File | undefined) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setLocalError("PDF 형식(.pdf) 파일만 업로드할 수 있습니다.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setLocalError("PDF 파일 크기는 최대 20MB까지 지원합니다.");
      return;
    }
    setLocalError(null);
    onAnalyzePdf(file);
  };

  return (
    <section className="rounded-3xl border border-indigo-100 bg-gradient-to-br from-indigo-50/90 via-white to-sky-50/70 p-5 shadow-sm sm:p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
            <Sparkles className="h-3.5 w-3.5" />
            직접 논문 분석하기
          </span>
          <h2 className="mt-2 text-xl font-bold text-slate-900">
            어려운 AI 논문, 비유로 3분 만에 이해하세요
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            arXiv 링크를 붙여넣거나 PDF 파일을 올리면 핵심 요약·일상 비유·용어 사전을 자동으로 만들어 드립니다.
          </p>
        </div>

        <div className="inline-flex self-start rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          <button
            type="button"
            onClick={() => {
              setMode("url");
              setLocalError(null);
            }}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              mode === "url"
                ? "bg-indigo-600 text-white"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Link2 className="h-3.5 w-3.5" />
            arXiv ID / URL
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("pdf");
              setLocalError(null);
            }}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              mode === "pdf"
                ? "bg-indigo-600 text-white"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileUp className="h-3.5 w-3.5" />
            PDF 업로드
          </button>
        </div>
      </div>

      {mode === "url" ? (
        <div className="mt-4">
          <form onSubmit={handleSubmitUrl} className="flex flex-col gap-2.5 sm:flex-row">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={disabled}
              placeholder="예: 1706.03762 또는 https://arxiv.org/abs/2401.12345"
              className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200 disabled:bg-slate-100"
            />
            <button
              type="submit"
              disabled={disabled}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Sparkles className="h-4 w-4" />
              쉬운 해설 생성
            </button>
          </form>

          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>추천 입문 논문:</span>
            {SAMPLE_PAPERS.map((sample) => (
              <button
                key={sample.id}
                type="button"
                disabled={disabled}
                onClick={() => {
                  setInputValue(sample.id);
                  onAnalyzeArxiv(sample.id);
                }}
                className="rounded-full border border-indigo-200 bg-white px-2.5 py-1 font-medium text-indigo-700 transition hover:bg-indigo-50 disabled:opacity-50"
              >
                {sample.label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            handleSelectedFile(e.dataTransfer.files?.[0]);
          }}
          onClick={() => !disabled && fileInputRef.current?.click()}
          className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-7 text-center transition ${
            dragActive
              ? "border-indigo-500 bg-indigo-50/70"
              : "border-slate-300 bg-white/80 hover:border-indigo-400 hover:bg-indigo-50/30"
          } ${disabled ? "pointer-events-none opacity-60" : ""}`}
        >
          <UploadCloud className="h-8 w-8 text-indigo-500" />
          <p className="mt-2 text-sm font-semibold text-slate-800">
            PDF 논문 파일을 여기로 끌어다 놓거나 클릭해서 선택하세요
          </p>
          <p className="mt-1 text-xs text-slate-500">
            최대 20MB · 동일 파일 재업로드 시 DB 캐시로 즉시 반환됩니다
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={(e) => {
              handleSelectedFile(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </div>
      )}

      {localError && (
        <p className="mt-2.5 text-xs font-medium text-rose-600">{localError}</p>
      )}
    </section>
  );
}
