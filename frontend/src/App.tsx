import { BookOpen, ClipboardList, History, MessageSquareText, Settings } from "lucide-react";
import { useState } from "react";
import FAQManager from "./pages/FAQManager";
import HistoryPage from "./pages/History";
import KnowledgeBase from "./pages/KnowledgeBase";
import ReplyWorkbench from "./pages/ReplyWorkbench";
import SettingsPage from "./pages/Settings";

const nav = [
  { key: "reply", label: "回复工作台", icon: MessageSquareText },
  { key: "knowledge", label: "知识库管理", icon: BookOpen },
  { key: "faq", label: "FAQ 管理", icon: ClipboardList },
  { key: "history", label: "历史记录", icon: History },
  { key: "settings", label: "系统设置", icon: Settings }
];

export default function App() {
  const [page, setPage] = useState("reply");
  const Current = page === "reply" ? ReplyWorkbench : page === "knowledge" ? KnowledgeBase : page === "faq" ? FAQManager : page === "history" ? HistoryPage : SettingsPage;

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">高校行政 AI 回复助手</h1>
            <p className="text-xs text-slate-500">网页半自动草稿生成，所有回复由老师审核后发送</p>
          </div>
          <div className="rounded-md bg-blue-50 px-3 py-1 text-xs text-blue-700">MVP</div>
        </div>
      </header>
      <div className="mx-auto flex max-w-7xl gap-6 px-6 py-6">
        <nav className="w-48 shrink-0 space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                onClick={() => setPage(item.key)}
                className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm ${page === item.key ? "bg-primary text-white" : "text-slate-700 hover:bg-white"}`}
              >
                <Icon size={16} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <main className="min-w-0 flex-1">
          <Current />
        </main>
      </div>
    </div>
  );
}
