import { Check, Clipboard, Search, Star, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, HistoryItem } from "../api/client";
import { Button, Input, Panel, PrimaryButton, Select } from "../components/ui";

const questionCategories = ["流程类", "材料类", "时间类", "系统类", "学籍类", "奖助学金类", "论文答辩类", "个人隐私类", "投诉申诉类", "其他"];

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [faqSavedId, setFaqSavedId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setItems(await api.listHistory(keyword, category));
    setSelected(new Set());
  }

  useEffect(() => {
    load();
  }, []);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selected.size === items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((item) => item.id)));
    }
  }

  async function saveAsFAQ(item: HistoryItem) {
    setError("");
    setMessage("");
    try {
      await api.createFAQ({
        question: item.student_question,
        answer: item.final_answer || item.ai_answer,
        category: item.category,
        allow_auto_reply: true
      });
      setFaqSavedId(item.id);
      setTimeout(() => setFaqSavedId(null), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存 FAQ 失败");
    }
  }

  async function deleteOne(id: number) {
    setError("");
    setMessage("");
    try {
      await api.deleteHistory(id);
      setMessage("已删除");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  }

  async function deleteSelected() {
    if (selected.size === 0) return;
    setError("");
    setMessage("");
    try {
      const result = await api.batchDeleteHistory([...selected]);
      setMessage(`已删除 ${result.deleted} 条记录`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  }

  return (
    <Panel
      title="历史记录"
      action={
        <div className="flex items-center gap-2">
          {message && <span className="text-xs text-emerald-700">{message}</span>}
          {error && <span className="text-xs text-red-600">{error}</span>}
          <Input className="w-52" placeholder="关键词" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
          <Select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">全部分类</option>
            {questionCategories.map((name) => <option key={name}>{name}</option>)}
          </Select>
          <Button onClick={load}><Search size={16} />筛选</Button>
        </div>
      }
    >
      {items.length > 0 && (
        <div className="mb-3 flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={selected.size === items.length}
              onChange={toggleSelectAll}
            />
            全选
          </label>
          {selected.size > 0 && (
            <PrimaryButton onClick={deleteSelected} className="bg-red-600 border-red-600 hover:bg-red-700">
              <Trash2 size={16} />
              删除选中 ({selected.size})
            </PrimaryButton>
          )}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <article key={item.id} className="rounded-md border border-slate-200 bg-white p-3">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 shrink-0"
                checked={selected.has(item.id)}
                onChange={() => toggleSelect(item.id)}
              />
              <div className="min-w-0 flex-1">
                <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded bg-slate-100 px-2 py-1">{item.category}</span>
                  <span>{Math.round(item.confidence * 100)}%</span>
                  <span className={item.need_human_review ? "text-amber-700" : "text-emerald-700"}>
                    {item.need_human_review ? "需人工核实" : "可审核使用"}
                  </span>
                  <span className="text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
                </div>
                <h3 className="font-medium text-slate-900">{item.student_question}</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{item.final_answer || item.ai_answer}</p>
                <div className="mt-3 flex gap-2">
                  <Button onClick={() => navigator.clipboard.writeText(item.final_answer || item.ai_answer)}>
                    <Clipboard size={15} />
                    复制
                  </Button>
                  <Button onClick={() => saveAsFAQ(item)} disabled={faqSavedId === item.id}>
                    {faqSavedId === item.id ? <Check size={15} /> : <Star size={15} />}
                    {faqSavedId === item.id ? "已保存" : "标记为常见问题"}
                  </Button>
                  <Button onClick={() => deleteOne(item.id)}>
                    <Trash2 size={15} />
                    删除
                  </Button>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}
