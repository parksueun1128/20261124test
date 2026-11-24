import { FormEvent, useState } from "react";
import { Bot, Loader2, Send, User } from "lucide-react";
import { askPaperQuestion } from "../api/paperApi";
import type { ChatMessage } from "../types/paper";

interface PaperQAChatProps {
  arxivId: string;
}

const STARTER_QUESTIONS = [
  "이 기술이 실생활 서비스 어디에 쓰일 수 있나요?",
  "핵심 아이디어를 중학생도 이해하게 한 번 더 비유해 주세요.",
  "기존 방법들의 가장 큰 한계점이 무엇이었나요?",
];

export function PaperQAChat({ arxivId }: PaperQAChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendQuestion = async (questionText: string) => {
    const trimmed = questionText.trim();
    if (!trimmed || loading) return;

    const nextHistory: ChatMessage[] = [
      ...messages,
      { role: "user", content: trimmed },
    ];
    setMessages(nextHistory);
    setInput("");
    setError(null);
    setLoading(true);

    try {
      const response = await askPaperQuestion(arxivId, trimmed, messages);
      setMessages([
        ...nextHistory,
        { role: "assistant", content: response.answer },
      ]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "답변을 생성하는 중 오류가 발생했습니다."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    void sendQuestion(input);
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
      <div className="flex items-center gap-2">
        <Bot className="h-5 w-5 text-indigo-600" />
        <h3 className="text-base font-bold text-slate-900">
          이 논문에 대해 더 궁금한 점 물어보기
        </h3>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        방금 분석한 논문 요약과 발췌 원문을 바탕으로 AI 튜터가 쉽게 답변해 드립니다.
      </p>

      {messages.length === 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {STARTER_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              disabled={loading}
              onClick={() => void sendQuestion(q)}
              className="rounded-xl border border-indigo-200 bg-indigo-50/60 px-3 py-2 text-left text-xs font-medium text-indigo-800 transition hover:bg-indigo-100"
            >
              “{q}”
            </button>
          ))}
        </div>
      )}

      {messages.length > 0 && (
        <div className="mt-4 max-h-96 space-y-3 overflow-y-auto rounded-2xl bg-slate-50 p-4">
          {messages.map((msg, idx) => (
            <div
              key={`${msg.role}-${idx}`}
              className={`flex items-start gap-2.5 ${
                msg.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                  msg.role === "user"
                    ? "bg-slate-800 text-white"
                    : "bg-indigo-600 text-white"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="h-4 w-4" />
                ) : (
                  <Bot className="h-4 w-4" />
                )}
              </div>
              <div
                className={`max-w-[82%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-slate-900 text-white"
                    : "border border-slate-200 bg-white text-slate-800"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-xs text-indigo-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              AI 튜터가 쉬운 답변을 정리하고 있습니다...
            </div>
          )}
        </div>
      )}

      {error && (
        <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
          {error}
        </p>
      )}

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          placeholder="논문 내용 중 이해되지 않는 부분을 자유롭게 물어보세요..."
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100 disabled:bg-slate-100"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          전송
        </button>
      </form>
    </div>
  );
}
