import { Edit3, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, FAQItem } from "../api/client";
import { Button, categories, Input, Panel, PrimaryButton, Select, Textarea } from "../components/ui";

const emptyForm = { question: "", answer: "", category: "其他", allow_auto_reply: true };

export default function FAQManager() {
  const [items, setItems] = useState<FAQItem[]>([]);
  const [keyword, setKeyword] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<number | null>(null);

  async function load() {
    setItems(await api.listFAQ(keyword));
  }

  useEffect(() => {
    load();
  }, []);

  async function submit() {
    if (!form.question || !form.answer) return;
    if (editing) {
      await api.updateFAQ(editing, form);
    } else {
      await api.createFAQ(form);
    }
    setForm(emptyForm);
    setEditing(null);
    await load();
  }

  function edit(item: FAQItem) {
    setEditing(item.id);
    setForm({
      question: item.question,
      answer: item.answer,
      category: item.category,
      allow_auto_reply: item.allow_auto_reply
    });
  }

  async function remove(id: number) {
    await api.deleteFAQ(id);
    await load();
  }

  return (
    <div className="space-y-4">
      <Panel title={editing ? "编辑 FAQ" : "新增 FAQ"}>
        <div className="grid gap-3 lg:grid-cols-2">
          <Textarea rows={4} placeholder="常见问题" value={form.question} onChange={(event) => setForm({ ...form, question: event.target.value })} />
          <Textarea rows={4} placeholder="标准答案" value={form.answer} onChange={(event) => setForm({ ...form, answer: event.target.value })} />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
            {categories.map((name) => <option key={name}>{name}</option>)}
          </Select>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={form.allow_auto_reply} onChange={(event) => setForm({ ...form, allow_auto_reply: event.target.checked })} />
            允许自动作为依据
          </label>
          <PrimaryButton onClick={submit}>
            <Plus size={16} />
            {editing ? "保存修改" : "新增 FAQ"}
          </PrimaryButton>
          {editing && <Button onClick={() => { setEditing(null); setForm(emptyForm); }}>取消</Button>}
        </div>
      </Panel>

      <Panel
        title="FAQ 列表"
        action={
          <div className="flex gap-2">
            <Input className="w-56" placeholder="搜索问题或答案" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
            <Button onClick={load}><Search size={16} />搜索</Button>
          </div>
        }
      >
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item.id} className="rounded-md border border-slate-200 p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-2">
                    <span className="rounded bg-slate-100 px-2 py-1 text-xs">{item.category}</span>
                    <span className={item.allow_auto_reply ? "text-xs text-emerald-700" : "text-xs text-slate-500"}>
                      {item.allow_auto_reply ? "允许自动回复" : "仅人工参考"}
                    </span>
                  </div>
                  <h3 className="font-medium text-slate-900">{item.question}</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{item.answer}</p>
                </div>
                <div className="flex gap-2">
                  <Button onClick={() => edit(item)}><Edit3 size={15} /></Button>
                  <Button onClick={() => remove(item.id)}><Trash2 size={15} /></Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
