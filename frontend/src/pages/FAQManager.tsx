import { Download, Edit3, Plus, Search, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { api, FAQItem } from "../api/client";
import { Button, categories, Input, Panel, PrimaryButton, Select, Textarea } from "../components/ui";

const emptyForm = { question: "", answer: "", category: "其他", allow_auto_reply: true };

export default function FAQManager() {
  const [items, setItems] = useState<FAQItem[]>([]);
  const [keyword, setKeyword] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);

  async function load() {
    setItems(await api.listFAQ(keyword));
  }

  useEffect(() => {
    load();
  }, []);

  async function submit() {
    if (!form.question || !form.answer) return;
    setMessage("");
    setError("");
    try {
      const payload = {
        ...form,
        question: form.question.trim(),
        answer: form.answer.trim()
      };
      if (editing) {
        await api.updateFAQ(editing, payload);
        setMessage("已保存 FAQ 修改");
      } else {
        await api.createFAQ(payload);
        setMessage("已新增 FAQ");
      }
      setForm(emptyForm);
      setEditing(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存 FAQ 失败");
    }
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
    setMessage("");
    setError("");
    try {
      await api.deleteFAQ(id);
      setMessage("已删除 FAQ");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除 FAQ 失败");
    }
  }

  async function importFAQ() {
    if (!file) return;
    setImporting(true);
    setMessage("");
    setError("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const result = await api.importFAQ(formData);
      setFile(null);
      setFileInputKey((current) => current + 1);
      setMessage(`已导入 ${result.imported} 条 FAQ`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入 FAQ 失败");
    } finally {
      setImporting(false);
    }
  }

  async function exportFAQ() {
    setExporting(true);
    setMessage("");
    setError("");
    try {
      const blob = await api.exportFAQ(keyword);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "faq-export.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMessage("已导出 FAQ");
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出 FAQ 失败");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-4">
      <Panel
        title={editing ? "编辑 FAQ" : "新增 FAQ"}
        action={
          <div className="text-xs">
            {message && <span className="text-emerald-700">{message}</span>}
            {error && <span className="text-red-600">{error}</span>}
          </div>
        }
      >
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

      <Panel title="导入导出 FAQ">
        <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
          <Input
            key={fileInputKey}
            type="file"
            accept=".xls,.xlsx"
            onChange={(event) => {
              setFile(event.target.files?.[0] || null);
              setMessage("");
              setError("");
            }}
          />
          <PrimaryButton onClick={importFAQ} disabled={!file || importing}>
            <Upload size={16} />
            {importing ? "导入中" : "导入 FAQ"}
          </PrimaryButton>
          <Button onClick={exportFAQ} disabled={exporting}>
            <Download size={16} />
            {exporting ? "导出中" : "导出 FAQ"}
          </Button>
        </div>
        {file && <p className="mt-2 text-xs text-slate-500">待导入文件：{file.name}</p>}
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
