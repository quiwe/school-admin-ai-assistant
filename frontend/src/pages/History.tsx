import { Clipboard, Search, Star, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, HistoryItem } from "../api/client";
import { Button, Input, Panel, Select } from "../components/ui";
import { copyToClipboard } from "../utils/clipboard";
import { displayText, previewText } from "../utils/text";

const questionCategories = ["流程类", "材料类", "时间类", "系统类", "学籍类", "奖助学金类", "论文答辩类", "个人隐私类", "投诉申诉类", "其他"];

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [savedFAQIds, setSavedFAQIds] = useState<number[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const data = await api.listHistory(keyword, category);
    setItems(data);
    setSelectedIds((current) => current.filter((id) => data.some((item) => item.id === id)));
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const refresh = () => {
      void load();
    };
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, 15000);
    window.addEventListener("history:changed", refresh);
    window.addEventListener("app:show-history", refresh);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("history:changed", refresh);
      window.removeEventListener("app:show-history", refresh);
    };
  }, [keyword, category]);

  async function saveAsFAQ(item: HistoryItem) {
    const answer = item.final_answer || item.ai_answer;
    if (!item.student_question.trim() || !answer.trim()) return;
    setMessage("");
    setError("");
    try {
      await api.createFAQ({
        question: item.student_question.trim(),
        answer: answer.trim(),
        category: item.category || "其他",
        allow_auto_reply: true
      });
      window.dispatchEvent(new Event("faq:changed"));
      setSavedFAQIds((current) => Array.from(new Set([...current, item.id])));
      setMessage("已保存到 FAQ 管理");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存 FAQ 失败");
    }
  }

  function toggleSelected(id: number) {
    setSelectedIds((current) => current.includes(id) ? current.filter((itemId) => itemId !== id) : [...current, id]);
  }

  function toggleAll() {
    setSelectedIds((current) => current.length === items.length ? [] : items.map((item) => item.id));
  }

  async function removeSelected() {
    if (!selectedIds.length) return;
    setMessage("");
    setError("");
    try {
      const result = await api.deleteHistory(selectedIds);
      setSelectedIds([]);
      setMessage(`已删除 ${result.deleted} 条历史记录`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除历史记录失败");
    }
  }

  async function removeOne(id: number) {
    setMessage("");
    setError("");
    try {
      await api.deleteHistoryItem(id);
      setSelectedIds((current) => current.filter((itemId) => itemId !== id));
      setMessage("已删除历史记录");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除历史记录失败");
    }
  }

  return (
    <Panel
      title="历史记录"
      action={
        <div className="flex flex-wrap gap-2">
          <Input className="w-full sm:w-40" placeholder="关键词" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
          <Select className="flex-1 sm:flex-none" value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">全部分类</option>
            {questionCategories.map((name) => <option key={name}>{name}</option>)}
          </Select>
          <Button onClick={load}><Search size={16} />筛选</Button>
        </div>
      }
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={items.length > 0 && selectedIds.length === items.length} onChange={toggleAll} />
            全选
          </label>
          <Button onClick={removeSelected} disabled={!selectedIds.length}>
            <Trash2 size={15} />
            删除选中
          </Button>
          {selectedIds.length > 0 && <span className="text-xs text-slate-500">已选择 {selectedIds.length} 条</span>}
        </div>
        <div className="text-xs">
          {message && <span className="text-emerald-700">{message}</span>}
          {error && <span className="text-red-600">{error}</span>}
        </div>
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <article key={item.id} className="rounded-md border border-slate-200 bg-white p-3">
            <div className="mb-2 flex items-start gap-3">
              <input
                className="mt-1"
                type="checkbox"
                checked={selectedIds.includes(item.id)}
                onChange={() => toggleSelected(item.id)}
                aria-label="选择历史问题"
              />
              <div className="min-w-0 flex-1">
                <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="safe-text rounded bg-slate-100 px-2 py-1">{displayText(item.category, "其他")}</span>
                  <span>{Math.round(item.confidence * 100)}%</span>
                  <span className={item.need_human_review ? "text-amber-700" : "text-emerald-700"}>
                    {item.need_human_review ? "需人工核实" : "可审核使用"}
                  </span>
                  <span className="text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
                </div>
                <h3 className="safe-text clamp-2 font-medium text-slate-900" title={displayText(item.student_question, "未填写问题")}>
                  {displayText(item.student_question, "未填写问题")}
                </h3>
                <p className="safe-text clamp-4 mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600" title={displayText(item.final_answer || item.ai_answer, "暂无回复")}>
                  {previewText(item.final_answer || item.ai_answer, 420, "暂无回复")}
                </p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button onClick={() => { void copyToClipboard(item.final_answer || item.ai_answer); }}>
                <Clipboard size={15} />
                <span className="hidden sm:inline">复制历史回复</span>
                <span className="sm:hidden">复制</span>
              </Button>
              <Button onClick={() => saveAsFAQ(item)} disabled={savedFAQIds.includes(item.id)}>
                <Star size={15} />
                <span className="hidden sm:inline">{savedFAQIds.includes(item.id) ? "已保存 FAQ" : "标记为常见问题"}</span>
                <span className="sm:hidden">FAQ</span>
              </Button>
              <Button onClick={() => removeOne(item.id)}>
                <Trash2 size={15} />
                <span className="hidden sm:inline">删除</span>
              </Button>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}
