import { Eye, RefreshCw, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, KnowledgeFile } from "../api/client";
import { Button, categories, Input, Panel, PrimaryButton, Select } from "../components/ui";

export default function KnowledgeBase() {
  const [items, setItems] = useState<KnowledgeFile[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState("其他");
  const [importFAQ, setImportFAQ] = useState(false);
  const [selected, setSelected] = useState<KnowledgeFile | null>(null);
  const [categoryDrafts, setCategoryDrafts] = useState<Record<number, string>>({});
  const [fileInputKey, setFileInputKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [savingCategoryId, setSavingCategoryId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const data = await api.listKnowledge();
    setItems(data);
    setCategoryDrafts(Object.fromEntries(data.map((item) => [item.id, item.category])));
  }

  useEffect(() => {
    load();
  }, []);

  async function upload() {
    if (!file) return;
    setError("");
    setMessage("");
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("category", category);
    form.append("import_faq", String(importFAQ));
    try {
      const saved = await api.uploadKnowledge(form);
      setFile(null);
      setFileInputKey((current) => current + 1);
      setMessage(`已保存到知识库：${saved.filename}，${saved.chunk_count} 个 chunk`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存知识库文件失败");
    } finally {
      setUploading(false);
    }
  }

  async function remove(id: number) {
    setError("");
    setMessage("");
    try {
      await api.deleteKnowledge(id);
      setMessage("已删除知识库文件");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  }

  async function reindex(id: number) {
    setError("");
    setMessage("");
    try {
      const updated = await api.reindexKnowledge(id);
      setMessage(`已重新索引：${updated.filename}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "重新索引失败");
    }
  }

  async function saveCategory(item: KnowledgeFile) {
    const nextCategory = categoryDrafts[item.id] || item.category;
    setError("");
    setMessage("");
    setSavingCategoryId(item.id);
    try {
      const updated = await api.updateKnowledge(item.id, { category: nextCategory });
      setMessage(`已保存分类：${updated.filename} / ${updated.category}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存分类失败");
    } finally {
      setSavingCategoryId(null);
    }
  }

  return (
    <div className="space-y-4">
      <Panel
        title="上传知识库文件"
        action={
          <div className="text-xs">
            {message && <span className="text-emerald-700">{message}</span>}
            {error && <span className="text-red-600">{error}</span>}
          </div>
        }
      >
        <div className="grid gap-3 md:grid-cols-[1fr_160px_auto_auto]">
          <Input
            key={fileInputKey}
            type="file"
            accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.xls,.xlsx"
            onChange={(event) => {
              setFile(event.target.files?.[0] || null);
              setMessage("");
              setError("");
            }}
          />
          <Select value={category} onChange={(event) => setCategory(event.target.value)}>
            {categories.map((name) => <option key={name}>{name}</option>)}
          </Select>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={importFAQ} onChange={(event) => setImportFAQ(event.target.checked)} />
            Excel 导入 FAQ
          </label>
          <PrimaryButton onClick={upload} disabled={!file || uploading}>
            <Save size={16} />
            {uploading ? "保存中" : "保存文件到知识库"}
          </PrimaryButton>
        </div>
        {file && <p className="mt-2 text-xs text-slate-500">待保存文件：{file.name}</p>}
      </Panel>

      <Panel title="文件列表">
        <div className="overflow-hidden rounded-md border border-slate-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2">文件名</th>
                <th className="px-3 py-2">分类</th>
                <th className="px-3 py-2">Chunk</th>
                <th className="px-3 py-2">状态</th>
                <th className="px-3 py-2">上传时间</th>
                <th className="px-3 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-slate-200">
                  <td className="px-3 py-2 font-medium">{item.filename}</td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Select
                        className="w-32"
                        value={categoryDrafts[item.id] || item.category}
                        onChange={(event) =>
                          setCategoryDrafts((current) => ({ ...current, [item.id]: event.target.value }))
                        }
                      >
                        {categories.map((name) => <option key={name}>{name}</option>)}
                      </Select>
                      <Button onClick={() => saveCategory(item)} disabled={savingCategoryId === item.id} title="保存分类">
                        <Save size={15} />
                        保存
                      </Button>
                    </div>
                  </td>
                  <td className="px-3 py-2">{item.chunk_count}</td>
                  <td className="px-3 py-2">{item.status}</td>
                  <td className="px-3 py-2">{new Date(item.upload_time).toLocaleString()}</td>
                  <td className="flex gap-2 px-3 py-2">
                    <Button onClick={() => setSelected(item)} title="查看解析内容"><Eye size={15} /></Button>
                    <Button onClick={() => reindex(item.id)} title="重新索引"><RefreshCw size={15} /></Button>
                    <Button onClick={() => remove(item.id)} title="删除"><Trash2 size={15} /></Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {selected && (
        <Panel title={`解析内容：${selected.filename}`} action={<Button onClick={() => setSelected(null)}>关闭</Button>}>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700">{selected.parsed_text}</pre>
        </Panel>
      )}
    </div>
  );
}
