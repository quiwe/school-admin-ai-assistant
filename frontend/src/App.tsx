import { BookOpen, ClipboardList, Download, ExternalLink, History, MessageSquareText, Settings, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, UpdateCheckResponse } from "./api/client";
import { Button, PrimaryButton } from "./components/ui";
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
  const [updateInfo, setUpdateInfo] = useState<UpdateCheckResponse | null>(null);
  const [updateDismissed, setUpdateDismissed] = useState(false);
  const [installingUpdate, setInstallingUpdate] = useState(false);
  const [updateMessage, setUpdateMessage] = useState("");

  useEffect(() => {
    api.checkUpdate()
      .then((data) => {
        if (data.has_update) {
          setUpdateInfo(data);
        }
      })
      .catch(() => undefined);
  }, []);

  async function installUpdate() {
    if (!updateInfo?.download_url) {
      openReleasePage(updateInfo?.release_url);
      return;
    }
    setInstallingUpdate(true);
    setUpdateMessage("正在下载安装包，请稍候...");
    try {
      const result = await api.installUpdate();
      setUpdateMessage(result.message);
    } catch (err) {
      setUpdateMessage(err instanceof Error ? err.message : "自动更新失败，请打开发布页手动下载。");
    } finally {
      setInstallingUpdate(false);
    }
  }

  function openReleasePage(url?: string) {
    if (url) {
      window.open(url, "_blank", "noopener,noreferrer");
    }
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-[1760px] items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">高校行政 AI 回复助手</h1>
            <p className="text-xs text-slate-500">桌面端半自动草稿生成，所有回复由老师审核后发送</p>
          </div>
          <div className="rounded-md bg-blue-50 px-3 py-1 text-xs text-blue-700">桌面版</div>
        </div>
      </header>
      {updateInfo?.has_update && !updateDismissed && (
        <section className="border-b border-amber-200 bg-amber-50">
          <div className="mx-auto flex w-full max-w-[1760px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
            <div className="min-w-0 text-sm text-amber-900">
              <div className="font-semibold">
                发现新版本 {updateInfo.latest_version}
                <span className="ml-2 font-normal text-amber-700">当前版本 {updateInfo.current_version}</span>
              </div>
              <div className="mt-1 line-clamp-2 text-xs leading-5 text-amber-800">
                {updateMessage || updateInfo.body || "建议更新到最新版本以获得修复和新功能。"}
              </div>
              {updateInfo.asset_size ? (
                <div className="mt-1 text-xs text-amber-700">安装包大小：{formatBytes(updateInfo.asset_size)}</div>
              ) : null}
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <PrimaryButton onClick={installUpdate} disabled={installingUpdate}>
                <Download size={16} />
                {installingUpdate ? "更新中" : "立即更新"}
              </PrimaryButton>
              <Button onClick={() => openReleasePage(updateInfo.release_url)}>
                <ExternalLink size={16} />
                发布页
              </Button>
              <Button onClick={() => setUpdateDismissed(true)} title="稍后提醒">
                <X size={16} />
                稍后
              </Button>
            </div>
          </div>
        </section>
      )}
      {updateInfo?.force_update && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-6">
          <section className="w-full max-w-lg rounded-lg bg-white p-5 shadow-2xl">
            <h2 className="text-base font-semibold text-slate-900">需要更新后继续使用</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              {updateInfo.update_required_message ||
                `当前版本 ${updateInfo.current_version} 已低于最低可用版本 ${updateInfo.min_supported_version || updateInfo.latest_version}，请更新后继续使用。`}
            </p>
            <div className="mt-4 rounded-md bg-slate-50 p-3 text-sm text-slate-600">
              当前版本：{updateInfo.current_version}
              <br />
              最新版本：{updateInfo.latest_version}
            </div>
            {updateMessage && <p className="mt-3 text-sm leading-6 text-amber-700">{updateMessage}</p>}
            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <Button onClick={() => openReleasePage(updateInfo.release_url)}>
                <ExternalLink size={16} />
                打开发布页
              </Button>
              <PrimaryButton onClick={installUpdate} disabled={installingUpdate}>
                <Download size={16} />
                {installingUpdate ? "更新中" : "立即更新"}
              </PrimaryButton>
            </div>
          </section>
        </div>
      )}
      <div className="mx-auto flex w-full max-w-[1760px] gap-4 px-4 py-5 sm:px-6 lg:gap-6 lg:px-8">
        <nav className="w-44 shrink-0 space-y-1 lg:w-48">
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
          <div className={page === "reply" ? "block" : "hidden"}>
            <ReplyWorkbench />
          </div>
          <div className={page === "knowledge" ? "block" : "hidden"}>
            <KnowledgeBase />
          </div>
          <div className={page === "faq" ? "block" : "hidden"}>
            <FAQManager />
          </div>
          <div className={page === "history" ? "block" : "hidden"}>
            <HistoryPage />
          </div>
          <div className={page === "settings" ? "block" : "hidden"}>
            <SettingsPage />
          </div>
        </main>
      </div>
    </div>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
