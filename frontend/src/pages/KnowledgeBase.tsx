import { Eye, RefreshCw, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { api, KnowledgeFile } from "../api/client";
import { Button, categories, Input, Panel, PrimaryButton, Select } from "../components/ui";

export default function KnowledgeBase() {
  const [items, setItems] = useState<KnowledgeFile[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState("其他");
  const [importFAQ, setImportFAQ] = useState(false);
  const [selected, setSelected] = useState<KnowledgeFile | null>(null);

  async function load() {
    setItems(await api.listKnowledge());
  }

  useEffect(() => {
    load();
  }, []);

  async function upload() {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("category", category);
    form.append("import_faq", String(importFAQ));
    await api.uploadKnowledge(form);
    setFile(null);
    await load();
  }

  async function remove(id: number) {
    await api.deleteKnowledge(id);
    await load();
  }

  async function reindex(id: number) {
    await api.reindexKnowledge(id);
    await load();
  }

  return (
    <div className="space-y-4">
      <Panel title="上传知识库文件">
        <div className="grid gap-3 md:grid-cols-[1fr_160px_auto_auto]">
          <Input type="file" accept=".pdf,.docx,.txt,.xlsx" onChange={(event) => setFile(event.target.files?.[0] || null)} />
          <Select value={category} onChange={(event) => setCategory(event.target.value)}>
            {categories.map((name) => <option key={name}>{name}</option>)}
          </Select>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={importFAQ} onChange={(event) => setImportFAQ(event.target.checked)} />
            XLSX 导入 FAQ
          </label>
          <PrimaryButton onClick={upload} disabled={!file}>
            <Upload size={16} />
            上传
          </PrimaryButton>
        </div>
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
                  <td className="px-3 py-2">{item.category}</td>
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
