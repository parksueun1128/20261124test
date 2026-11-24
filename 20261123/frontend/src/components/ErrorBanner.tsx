import { AlertCircle, RefreshCw, X } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ErrorBanner({ message, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-900 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
        <div>
          <p className="text-sm font-semibold">요청을 처리하지 못했습니다</p>
          <p className="mt-0.5 text-sm text-rose-700">{message}</p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2 self-end sm:self-center">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-rose-700"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            다시 시도
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="오류 메시지 닫기"
            className="rounded-lg p-1.5 text-rose-500 transition hover:bg-rose-100 hover:text-rose-800"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
