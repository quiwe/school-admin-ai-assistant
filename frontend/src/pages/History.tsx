import { Clipboard, Search, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { api, HistoryItem } from "../api/client";
import { Button, Input, Panel, Select } from "../components/ui";

const questionCategories = ["流程类", "材料类", "时间类", "系统类", "学籍类", "奖助学金类", "论文答辩类", "个人隐私类", "投诉申诉类", "其他"];

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");

  async function load() {
    setItems(await api.listHistory(keyword, category));
  }

  useEffect(() => {
    load();
  }, []);

  async function saveAsFAQ(item: HistoryItem) {
    await api.createFAQ({
      question: item.student_question,
      answer: item.final_answer || item.ai_answer,
      category: item.category,
      allow_auto_reply: true
    });
  }

  return (
    <Panel
      title="历史记录"
      action={
        <div className="flex gap-2">
          <Input className="w-52" placeholder="关键词" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
          <Select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">全部分类</option>
            {questionCategories.map((name) => <option key={name}>{name}</option>)}
          </Select>
          <Button onClick={load}><Search size={16} />筛选</Button>
        </div>
      }
    >
      <div className="space-y-3">
        {items.map((item) => (
          <article key={item.id} className="rounded-md border border-slate-200 bg-white p-3">
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
                复制历史回复
              </Button>
              <Button onClick={() => saveAsFAQ(item)}>
                <Star size={15} />
                标记为常见问题
              </Button>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}
