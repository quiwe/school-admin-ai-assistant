import { AlertCircle, Bot, Loader2, Send, UserRound } from "lucide-react";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { api } from "../api/client";

type ChatMessage = {
  id: string;
  role: "student" | "assistant";
  content: string;
  status?: "loading" | "error";
};

function newMessage(role: ChatMessage["role"], content: string, status?: ChatMessage["status"]): ChatMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    role,
    content,
    status
  };
}

export default function StudentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const accessKey = new URLSearchParams(window.location.search).get("access_key") || "";

  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth"
    });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
    if (!accessKey) {
      setMessages([
        newMessage("assistant", "链接缺少访问码，请使用老师提供的完整网页端地址进入。", "error")
      ]);
    }
  }, []);

  async function sendQuestion(event?: FormEvent) {
    event?.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || loading) return;
    if (!accessKey) {
      setMessages((current) => [
        ...current,
        newMessage("assistant", "链接缺少访问码，请使用老师提供的完整网页端地址进入。", "error")
      ]);
      return;
    }

    const loadingMessage = newMessage("assistant", "正在回复...", "loading");
    setMessages((current) => [
      ...current,
      newMessage("student", trimmedQuestion),
      loadingMessage
    ]);
    setQuestion("");
    setLoading(true);

    try {
      const data = await api.generateStudentReply(trimmedQuestion, accessKey);
      setMessages((current) =>
        current.map((message) =>
          message.id === loadingMessage.id
            ? { ...message, content: data.answer, status: undefined }
            : message
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "回复生成失败，请稍后再试。";
      setMessages((current) =>
        current.map((message) =>
          message.id === loadingMessage.id
            ? { ...message, content: errorMessage, status: "error" }
            : message
        )
      );
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendQuestion();
    }
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#eef3f8]">
      <header className="shrink-0 border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 w-full max-w-4xl items-center gap-3 px-4 sm:px-6">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-blue-600 text-white">
            <Bot size={22} />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold text-slate-900">学生咨询助手</h1>
            <p className="truncate text-xs text-slate-500">高校行政 AI 回复助手网页端</p>
          </div>
        </div>
      </header>

      <main ref={listRef} className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col gap-4 px-4 py-5 sm:px-6">
          {messages.length === 0 ? (
            <div className="flex flex-1 items-center justify-center">
              <div className="max-w-sm text-center text-sm leading-6 text-slate-500">
                请输入咨询问题，回复会显示在这里。
              </div>
            </div>
          ) : (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          )}
        </div>
      </main>

      <footer className="shrink-0 border-t border-slate-200 bg-white">
        <form onSubmit={sendQuestion} className="mx-auto flex w-full max-w-4xl items-end gap-3 px-4 py-4 sm:px-6">
          <textarea
            ref={inputRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!accessKey}
            rows={1}
            placeholder="请输入问题"
            className="max-h-36 min-h-11 flex-1 resize-none rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm leading-6 text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
          />
          <button
            type="submit"
            disabled={!question.trim() || loading || !accessKey}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-blue-600 text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            title="发送"
            aria-label="发送"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
          </button>
        </form>
      </footer>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isStudent = message.role === "student";
  const Icon = isStudent ? UserRound : message.status === "error" ? AlertCircle : Bot;

  return (
    <article className={`flex items-end gap-2 ${isStudent ? "justify-end" : "justify-start"}`}>
      {!isStudent && (
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${
            message.status === "error" ? "bg-red-100 text-red-700" : "bg-white text-blue-600"
          }`}
        >
          <Icon size={18} />
        </div>
      )}
      <div
        className={`max-w-[78%] whitespace-pre-wrap break-words rounded-lg px-4 py-3 text-sm leading-6 shadow-sm sm:max-w-[70%] ${
          isStudent
            ? "bg-blue-600 text-white"
            : message.status === "error"
              ? "border border-red-200 bg-red-50 text-red-700"
              : "bg-white text-slate-800"
        }`}
      >
        {message.content}
      </div>
      {isStudent && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-blue-600 text-white">
          <Icon size={18} />
        </div>
      )}
    </article>
  );
}
